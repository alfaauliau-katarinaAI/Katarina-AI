// Katarina AI — read-only broker quote/trade session evidence collector.
// Run manually on one authorized MT5 chart. Never sends orders or rewrites state.
// Logs stay in the local MT5 Experts/Journal; do not publish raw broker/account logs.
#property strict
#property version "1.00"
#property script_show_inputs

input string InpSymbols = "XAUUSD.vx,NAS100.vx,EURUSD.vx,GBPUSD.vx,USDJPY.vx";
input int InpMaxSessionsPerDay = 16;

// A missing entry is NOT proof that a market was closed.
// Timestamps from SymbolInfoSession* are broker-session offsets from midnight,
// not epoch UTC; preserve their original integer values for verification.
void PrintSessions(const string symbol,
                   const ENUM_DAY_OF_WEEK day,
                   const bool is_quote)
  {
   string kind = (is_quote ? "QUOTE" : "TRADE");
   int found = 0;
   for(uint idx=0;idx<(uint)InpMaxSessionsPerDay;idx++)
     {
      datetime from_time=0;
      datetime to_time=0;
      ResetLastError();
      bool ok = (is_quote
                 ? SymbolInfoSessionQuote(symbol,day,idx,from_time,to_time)
                 : SymbolInfoSessionTrade(symbol,day,idx,from_time,to_time));
      if(!ok)
         break;
      PrintFormat("KATARINA_SESSION|symbol=%s|kind=%s|weekday=%d|index=%d|from_seconds=%s|to_seconds=%s|status=OBSERVED",
                  symbol,kind,(int)day,(int)idx,
                  IntegerToString((long)from_time),
                  IntegerToString((long)to_time));
      found++;
     }
   if(found==0)
      PrintFormat("KATARINA_SESSION|symbol=%s|kind=%s|weekday=%d|status=NO_SESSION_OR_UNAVAILABLE",
                  symbol,kind,(int)day);
  }

void OnStart()
  {
   if(InpMaxSessionsPerDay<1 || InpMaxSessionsPerDay>48)
     {
      Print("KATARINA_SESSION_PROBE|ERROR|INVALID_MAX_SESSIONS");
      return;
     }
   string symbols[];
   int count=StringSplit(InpSymbols,',',symbols);
   if(count<=0)
     {
      Print("KATARINA_SESSION_PROBE|ERROR|NO_SYMBOLS");
      return;
     }
   // These values are local, operator-only evidence; they are not a time
   // attestation or an automatic authorization to change Stage0 scoring.
   PrintFormat("KATARINA_SESSION_PROBE|START|server=%s|captured_server=%s|captured_utc=%s|symbol_count=%d",
               AccountInfoString(ACCOUNT_SERVER),
               TimeToString(TimeTradeServer(),TIME_DATE|TIME_SECONDS),
               TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),
               count);
   for(int i=0;i<count;i++)
     {
      string symbol=symbols[i];
      StringReplace(symbol," ","");
      bool is_custom=false;
      if(symbol=="" || !SymbolExist(symbol,is_custom))
        {
         PrintFormat("KATARINA_SESSION_PROBE|SYMBOL_UNAVAILABLE|symbol=%s",symbol);
         continue;
        }
      for(int d=0;d<7;d++)
        {
         PrintSessions(symbol,(ENUM_DAY_OF_WEEK)d,true);
         PrintSessions(symbol,(ENUM_DAY_OF_WEEK)d,false);
        }
     }
   Print("KATARINA_SESSION_PROBE|END|READ_ONLY|NO_TRADES");
  }
