// Katarina Stage 0 - broker quote/trade session evidence capture (read-only).
// Run manually as a SCRIPT on an approved RESEARCH MT5 terminal, never as an EA.
// Reads symbol metadata only. Does not place orders or activate trading.
// Output stays in the terminal's MQL5/Files sandbox. It is NOT certified UTC/DST evidence.
// Broker schedule is weekly and does not prove holidays, historical applicability or
// validity. Review the exported rows with independent broker documentation.
#property strict
#property script_show_inputs
#property version "1.00"

input string InpSymbols = "XAUUSD.vx,NAS100.vx,US30.vx,JPN225.vx,EURUSD.vx,GBPUSD.vx,USDJPY.vx";
input string InpOutputFile = "Katarina\\stage0-broker-sessions.csv";
#define MAX_SESSIONS_PER_DAY 32

void OnStart()
{
   int file = FileOpen(InpOutputFile, FILE_WRITE | FILE_CSV | FILE_ANSI, ';', CP_UTF8);
   if(file == INVALID_HANDLE)
   {
      PrintFormat("STAGE0_SESSION_CAPTURE_BLOCKED FILE_OPEN_ERROR %d", GetLastError());
      return;
   }
   FileWrite(file, "record_type", "broker_server", "captured_host_utc",
             "broker_wall_time", "symbol", "weekday_mon0", "kind",
             "session_index", "from_seconds", "to_seconds", "status", "error_code");
   string server = AccountInfoString(ACCOUNT_SERVER);
   // TimeGMT() and TimeTradeServer() depend on terminal/host configuration.
   // These are snapshots to cross-check, NOT independently verified UTC offsets.
   string host_utc = TimeToString(TimeGMT(), TIME_DATE | TIME_SECONDS);
   string broker_wall = TimeToString(TimeTradeServer(), TIME_DATE | TIME_SECONDS);
   FileWrite(file, "META", server, host_utc, broker_wall,
             "", "", "", "", "", "", "HOST_CLOCK_UNVERIFIED", "");

   string symbols[];
   int count = StringSplit(InpSymbols, (ushort)',', symbols);
   if(count <= 0 || StringLen(server) == 0)
   {
      FileWrite(file, "ERROR", server, host_utc, broker_wall,
                "", "", "", "", "", "", "EMPTY_SYMBOLS_OR_SERVER", "");
      FileClose(file);
      Print("STAGE0_SESSION_CAPTURE_BLOCKED INVALID_INPUT");
      return;
   }
   int observed = 0;
   for(int i = 0; i < count; i++)
   {
      string symbol = symbols[i];
      StringTrimLeft(symbol);
      StringTrimRight(symbol);
      if(StringLen(symbol) == 0)
      {
         FileWrite(file, "ERROR", server, host_utc, broker_wall,
                   "", "", "", "", "", "", "EMPTY_SYMBOL", "");
         continue;
      }
      for(int broker_day = 0; broker_day < 7; broker_day++)
      {
         ENUM_DAY_OF_WEEK day = (ENUM_DAY_OF_WEEK)broker_day;
         // MQL5: Sunday=0. Katarina's Python broker model: Monday=0.
         int monday_zero = (broker_day + 6) % 7;
         for(int kind = 0; kind < 2; kind++)
         {
            string category = (kind == 0 ? "quote" : "trade");
            bool ended = false;
            for(int index = 0; index < MAX_SESSIONS_PER_DAY; index++)
            {
               datetime from = 0, to = 0;
               ResetLastError();
               bool ok = (kind == 0)
                  ? SymbolInfoSessionQuote(symbol, day, (uint)index, from, to)
                  : SymbolInfoSessionTrade(symbol, day, (uint)index, from, to);
               if(!ok)
               {
                  if(index == 0)
                     FileWrite(file, "NO_SESSION_OR_UNAVAILABLE", server,
                               host_utc, broker_wall, symbol, monday_zero, category,
                               0, "", "", "UNVERIFIED", GetLastError());
                  ended = true;
                  break;
               }
               // Docs: session values are seconds since broker midnight; do not
               // strip the 24:00 or overnight endpoint with modulo 86400.
               FileWrite(file, "SESSION", server, host_utc, broker_wall,
                         symbol, monday_zero, category, index,
                         (long)from, (long)to, "REPORTED", "");
               observed++;
            }
            if(!ended)
               FileWrite(file, "SESSION_LIMIT_REACHED", server, host_utc,
                         broker_wall, symbol, monday_zero, category,
                         MAX_SESSIONS_PER_DAY, "", "", "UNVERIFIED", "");
         }
      }
   }
   FileFlush(file);
   FileClose(file);
   PrintFormat("STAGE0_SESSION_CAPTURE_DONE sessions=%d file=MQL5/Files/%s; evidence remains UNVERIFIED",
               observed, InpOutputFile);
}
