// FIVE CORE only. Opposite engines compiler-disabled. ADR sizing is Python PAPER manifest, not this EA.
//+------------------------------------------------------------------+
//| P9V2RobustFiveResearchShadow.mq5                                   |
//| Katarina AI / research-only V3 signal verifier.                   |
//| NEVER sends broker orders and never changes locked P9 V2 / P7.   |
//| H4 closed ATR-relative routing Growth vs Defensive for 3 engines.|
//| Two opposite SELL research methods, distinct original risk slots.|
//+------------------------------------------------------------------+
#property strict
#property version "2.210"
#property description "P9 V2 Robust FIVE research shadow ONLY. NO ORDERS."
input string InpSymbols="XAUUSD.vx,NAS100.vx,EURJPY.vx,USDCHF.vx";
input int InpTimerSeconds=30;
input double InpATRRegimeThreshold=1.0;
input double InpPaperRiskCapPercent=0.25;
input bool InpShowEachRegime=true;
const bool InpEnableEURSellPaper=false; // HARD_DISABLED_FIVE_ENGINE
const bool InpEnableCHFSellPaper=false; // HARD_DISABLED_FIVE_ENGINE
const bool InpEnableXAUSellBOSPullbackPaper=false; // HARD_DISABLED_FIVE_ENGINE
const bool InpEnableNASBuyH4MACDPaper=false; // HARD_DISABLED_FIVE_ENGINE // OPTIONAL: worsens stress robustness

enum MARKET_STATE {ST_BEAR=-1,ST_SIDEWAYS=0,ST_BULL=1,ST_TRANSITION=2};
struct SymbolSlot
{
 string name;
 int h4ema20,h4ema50,h4ema200,h4macd,h4adx,h4atr,h4rsi;
 int h1ema20,h1ema50,h1macd,h1adx,h1rsi,h1atr;
 datetime lastH1,lastH4;
 double atrRelative;
 MARKET_STATE state;
 string selectedEngine;
 string lastSignal;
 int paperN;
};
SymbolSlot M[];
int Count=0;
double ind(const int h,const int b,const int shift)
{
 double a[];
 if(h==INVALID_HANDLE || CopyBuffer(h,b,shift,1,a)!=1)return EMPTY_VALUE;
 return a[0];
}
bool valid(const double x)
{
 return x!=EMPTY_VALUE && MathIsValidNumber(x);
}
string Regime(const MARKET_STATE st)
{
 if(st==ST_BULL)return "BULL";
 if(st==ST_BEAR)return "BEAR";
 if(st==ST_SIDEWAYS)return "SIDEWAYS";
 return "TRANSITION";
}
double ATRMeanRatio(const int idx)
{
 double current=ind(M[idx].h4atr,0,1);
 if(!valid(current)||current<=0)return EMPTY_VALUE;
 double v[];
 if(CopyBuffer(M[idx].h4atr,0,2,60,v)!=60)return EMPTY_VALUE;
 double sum=0.0;
 for(int j=0;j<60;j++)sum+=v[j];
 return sum>0?current/(sum/60.0):EMPTY_VALUE;
}
double ATRRelative(const int idx)
{
 double current=ind(M[idx].h4atr,0,1);
 if(!valid(current)||current<=0)return EMPTY_VALUE;
 double v[];
 if(CopyBuffer(M[idx].h4atr,0,2,60,v)!=60)return EMPTY_VALUE;
 ArraySort(v);
 double median=.5*(v[29]+v[30]);
 return median>0?current/median:EMPTY_VALUE;
}
double maxHigh(const MqlRates &r[],const int start,const int n)
{
 double h=-DBL_MAX;
 for(int j=start;j<start+n;j++)h=MathMax(h,r[j].high);
 return h;
}
double minLow(const MqlRates &r[],const int start,const int n)
{
 double l=DBL_MAX;
 for(int j=start;j<start+n;j++)l=MathMin(l,r[j].low);
 return l;
}
double tickMedian100(const MqlRates &r[])
{
 double a[];ArrayResize(a,100);
 for(int j=0;j<100;j++)a[j]=(double)r[j+2].tick_volume;
 ArraySort(a);
 return .5*(a[49]+a[50]);
}
void logPaper(const int idx,const string side,const string method,const string setup,
 const datetime closedTime,const string reason)
{
 M[idx].paperN++;
 M[idx].lastSignal=side+" "+method;
 PrintFormat("P9_V2_ROBUST|SHADOW_ONLY|SYMBOL=%s|SIDE=%s|METHOD=%s|SETUP=%s|H4_ATR_REL=%.3f|REGIME=%s|BAR=%s|REASON=%s|RISK_CAP_REFERENCE=%.2f%%|NO_ORDER",
 M[idx].name,side,method,setup,M[idx].atrRelative,Regime(M[idx].state),
 TimeToString(closedTime,TIME_DATE|TIME_MINUTES),reason,InpPaperRiskCapPercent);
}
MARKET_STATE marketState(const int idx,const MqlRates &r[])
{
 double a=ind(M[idx].h4adx,0,1),p=ind(M[idx].h4adx,1,1),n=ind(M[idx].h4adx,2,1);
 double em20=ind(M[idx].h4ema20,0,1),em50=ind(M[idx].h4ema50,0,1);
 double m=ind(M[idx].h4macd,0,1),sg=ind(M[idx].h4macd,1,1);
 if(!valid(a)||!valid(p)||!valid(n)||!valid(em20)||!valid(em50)||!valid(m)||!valid(sg))return ST_TRANSITION;
 if(a<18)return ST_SIDEWAYS;
 if(r[1].close>em20 && em20>em50 && p>n && m>sg)return ST_BULL;
 if(r[1].close<em20 && em20<em50 && n>p && m<sg)return ST_BEAR;
 return ST_TRANSITION;
}
bool isGrowth(const int idx)
{
 return valid(M[idx].atrRelative) && M[idx].atrRelative<InpATRRegimeThreshold;
}
void H4Decision(const int idx,const MqlRates &r[])
{
 string s=M[idx].name;
 bool growth=isGrowth(idx);
 M[idx].selectedEngine=growth?"GROWTH":"DEFENSIVE";
 double m=ind(M[idx].h4macd,0,1),m0=ind(M[idx].h4macd,0,2);
 double sig=ind(M[idx].h4macd,1,1),sig0=ind(M[idx].h4macd,1,2);
 double adx=ind(M[idx].h4adx,0,1);
 double plus=ind(M[idx].h4adx,1,1),minus=ind(M[idx].h4adx,2,1);
 double ema20=ind(M[idx].h4ema20,0,1),ema50=ind(M[idx].h4ema50,0,1);
 double ema200=ind(M[idx].h4ema200,0,1);
 double atr=ind(M[idx].h4atr,0,1),rsi=ind(M[idx].h4rsi,0,1),prevrsi=ind(M[idx].h4rsi,0,2);
 if(!valid(m)||!valid(m0)||!valid(sig)||!valid(sig0)||!valid(adx)||!valid(ema20)||!valid(ema50)||
  !valid(ema200)||!valid(atr)||!valid(rsi)||!valid(prevrsi)||!valid(plus)||!valid(minus))return;
 datetime stamp=r[1].time;
 if(StringFind(s,"XAUUSD")==0)
 {
  // Keltner bullish breakout, MACD>signal, EMA50>EMA200.
  // Growth additionally requires ADX>=15; Defensive does not.
  bool breakout=(r[1].close>ema20+1.5*atr);
  if(breakout && m>sig && ema50>ema200 && (!growth || adx>=15))
   logPaper(idx,"BUY","XAU_H4_KELTNER",M[idx].selectedEngine,stamp,"CLOSED_H4_TREND_BREAKOUT");
 }
 if(StringFind(s,"NAS100")==0)
 {
  // Original SELL MACD crosses negative zero on latest completed H4.
  // Growth ADX>=15<30; Defensive ADX>=20<30. No NAS BUY in Pareto V3.
  double minADX=growth?15:20;
  if(m0>=0 && m<0 && m<sig && adx>=minADX && adx<30)
   logPaper(idx,"SELL","NAS_H4_MACD_ZERO",M[idx].selectedEngine,stamp,"CLOSED_H4_ZERO_CROSS");
  // Optional H4 BUY engine is DIFFERENT from original NAS H4 SELL.
  // It is not robust under severe costs in V3 backtest and is disabled by default.
  double ratioMean=ATRMeanRatio(idx);
  bool meanLowVol=valid(ratioMean) && ratioMean<1.0;
  if(InpEnableNASBuyH4MACDPaper && meanLowVol && m0<=sig0 && m>sig)
   logPaper(idx,"BUY","NAS_H4_MACD_SIGNAL_CROSS","OPTIONAL_OPPOSITE_PAPER",
       stamp,"H4_MACD_CROSSES_SIGNAL_UP_AND_ATR_BELOW_PRIOR_60_MEAN");
 }
 if(StringFind(s,"EURJPY")==0)
 {
  // Original BUY Momentum24 preserved.
  double p=SymbolInfoDouble(s,SYMBOL_POINT);
  double currentSpread=(double)SymbolInfoInteger(s,SYMBOL_SPREAD)*p;
  if(r[1].close>r[25].close && r[2].close<=r[26].close &&
     adx>=20 && atr>0 && currentSpread/atr<.08)
    logPaper(idx,"BUY","EUR_H4_MOMENTUM24","ORIGINAL",stamp,"CLOSED_H4_MOMENTUM");
 }
 if(StringFind(s,"USDCHF")==0)
 {
  if(prevrsi<=30 && rsi>30 && r[1].tick_volume>=1.25*tickMedian100(r))
   logPaper(idx,"BUY","CHF_H4_RSI14_REENTRY","ORIGINAL",stamp,"RSI_REENTRY_TICK");
  if(InpEnableCHFSellPaper && m0>=0 && m<0 && m<sig && ema20<ema50 && ema50<ema200)
   logPaper(idx,"SELL","CHF_H4_MACD_ZERO_EMA","ADAPTIVE_OPPOSITE",stamp,"MACD_ZERO_BELOW_EMA_STACK");
 }
}
void H1Decision(const int idx)
{
 string s=M[idx].name;
 if(StringFind(s,"XAUUSD")!=0 && StringFind(s,"EURJPY")!=0)return;
 MqlRates r[];
 ArraySetAsSeries(r,true);
 if(CopyRates(s,PERIOD_H1,0,110,r)<105)return;
 if(M[idx].lastH1==r[1].time)return;
 M[idx].lastH1=r[1].time;
 double macd=ind(M[idx].h1macd,0,1),signal=ind(M[idx].h1macd,1,1);
 double a=ind(M[idx].h1adx,0,1),p=ind(M[idx].h1adx,1,1),n=ind(M[idx].h1adx,2,1);
 double em20=ind(M[idx].h1ema20,0,1),em50=ind(M[idx].h1ema50,0,1);
 double rsi=ind(M[idx].h1rsi,0,1);
 double atrh1=ind(M[idx].h1atr,0,1);
 if(!valid(macd)||!valid(signal)||!valid(a)||!valid(p)||!valid(n)||
  !valid(em20)||!valid(em50)||!valid(rsi)||!valid(atrh1))return;
 if(StringFind(s,"XAUUSD")==0)
 {
  if(r[1].close>maxHigh(r,2,48) && a>=25 && macd>signal)
  {
   bool growth=isGrowth(idx);
   double h4em20=ind(M[idx].h4ema20,0,1),h4em50=ind(M[idx].h4ema50,0,1);
   bool allowed=growth ? valid(h4em20)&&valid(h4em50)&&h4em20>h4em50 :
       rsi>=50 && rsi<=70;
   if(allowed)
    logPaper(idx,"BUY","XAU_H1_DONCHIAN48",growth?"GROWTH":"DEFENSIVE",
      r[1].time,"CLOSED_H1_BREAKOUT");
  }
  // New opposite: XAUUSD SELL if a previously CONFIRMED H1 bearish
  // BOS12 occurred in one of the last 8 bars, price now rejects H1 EMA20,
  // with H1 bearish MACD/DI/ADX and H4 EMA+DI direction agreement.
  // This matches concept of Python candidate, no trading operations.
  if(InpEnableXAUSellBOSPullbackPaper)
  {
   bool priorBOS=false;
   for(int shift=2;shift<=9;shift++)
   {
    if(r[shift].close<minLow(r,shift+1,12))
    { priorBOS=true;break; }
   }
   double h4e20=ind(M[idx].h4ema20,0,1),h4e50=ind(M[idx].h4ema50,0,1);
   double h4plus=ind(M[idx].h4adx,1,1),h4minus=ind(M[idx].h4adx,2,1);
   bool h4Bear=valid(h4e20)&&valid(h4e50)&&valid(h4plus)&&valid(h4minus)&&
        h4e20<h4e50 && h4minus>h4plus;
   bool h1Bear=(em20<em50 && n>p && macd<signal && a>=16 &&
      r[1].high>=em20 && r[1].close<em20 &&
      r[1].close-r[1].open < -0.25*atrh1);
   if(priorBOS && h4Bear && h1Bear)
    logPaper(idx,"SELL","XAU_H1_BOS12_PULLBACK","NEW_OPPOSITE_RESEARCH",
       r[1].time,"PRIOR_8_BOS12_H1_EMA20_REJECTION_H4_DI_EMA");
  }
 }
 if(StringFind(s,"EURJPY")==0 && InpEnableEURSellPaper)
 {
  // New SELLS: H1 EMA20 bearish rejection, H1 MACD/DI/ADX/RSI.
  // MACD_TREND on last fully CLOSED H4: MACD<signal, minus DI>plus DI, EMA20<EMA50.
  double hm=ind(M[idx].h4macd,0,1),hs=ind(M[idx].h4macd,1,1);
  double hp=ind(M[idx].h4adx,1,1),hn=ind(M[idx].h4adx,2,1);
  double he20=ind(M[idx].h4ema20,0,1),he50=ind(M[idx].h4ema50,0,1);
  bool h4Bear=valid(hm)&&valid(hs)&&valid(hp)&&valid(hn)&&valid(he20)&&valid(he50)&&
      hm<hs && hn>hp && he20<he50;
  bool h1Bear=r[1].high>=em20 && r[1].close<em20 && r[1].close<r[1].open &&
      em20<em50 && macd<signal && n>p && a>=18 && rsi<52;
  if(h4Bear && h1Bear)
   logPaper(idx,"SELL","EUR_H1_EMA20_REJECTION","ADAPTIVE_OPPOSITE",
     r[1].time,"H4_MACD_DI_EMA_PLUS_H1_REJECTION");
 }
}
void update()
{
 string d="KATARINA P9 V2 ROBUST FIVE - SHADOW ONLY\nNever executes trades / NO_ORDER\n";
 for(int i=0;i<Count;i++)
 {
  MqlRates h4[];ArraySetAsSeries(h4,true);
  if(CopyRates(M[i].name,PERIOD_H4,0,140,h4)<130)
  {
   d+=M[i].name+" WAIT_H4_HISTORY\n";continue;
  }
  M[i].atrRelative=ATRRelative(i);
  if(M[i].lastH4!=h4[1].time)
  {
   M[i].lastH4=h4[1].time;
   M[i].state=marketState(i,h4);
   if(InpShowEachRegime)
    PrintFormat("P9_V2_ROBUST|STATE|SYMBOL=%s|H4_BAR=%s|ATRRATIO=%.3f|GROWTH=%d|REGIME=%s|NO_ORDER",
      M[i].name,TimeToString(h4[1].time,TIME_DATE|TIME_MINUTES),
      M[i].atrRelative,(int)isGrowth(i),Regime(M[i].state));
   H4Decision(i,h4);
  }
  H1Decision(i);
  d+=M[i].name+" "+Regime(M[i].state)+" ATR_R="+DoubleToString(M[i].atrRelative,2)+
      " | "+M[i].lastSignal+"\n";
 }
 Comment(d);
}
int OnInit()
{
 if(InpTimerSeconds<5||InpPaperRiskCapPercent<=0||InpPaperRiskCapPercent>0.25||
   InpATRRegimeThreshold<=0.4||InpATRRegimeThreshold>=2.0)return INIT_PARAMETERS_INCORRECT;
 string sym[];
 Count=StringSplit(InpSymbols,',',sym);
 if(Count!=4)return INIT_PARAMETERS_INCORRECT;
 ArrayResize(M,Count);
 for(int i=0;i<Count;i++)
 {
  M[i].name=sym[i];StringTrimLeft(M[i].name);StringTrimRight(M[i].name);
  if(!SymbolSelect(M[i].name,true))return INIT_FAILED;
  M[i].h4ema20=iMA(M[i].name,PERIOD_H4,20,0,MODE_EMA,PRICE_CLOSE);
  M[i].h4ema50=iMA(M[i].name,PERIOD_H4,50,0,MODE_EMA,PRICE_CLOSE);
  M[i].h4ema200=iMA(M[i].name,PERIOD_H4,200,0,MODE_EMA,PRICE_CLOSE);
  M[i].h4macd=iMACD(M[i].name,PERIOD_H4,12,26,9,PRICE_CLOSE);
  M[i].h4adx=iADX(M[i].name,PERIOD_H4,14);
  M[i].h4atr=iATR(M[i].name,PERIOD_H4,14);
  M[i].h4rsi=iRSI(M[i].name,PERIOD_H4,14,PRICE_CLOSE);
  M[i].h1ema20=iMA(M[i].name,PERIOD_H1,20,0,MODE_EMA,PRICE_CLOSE);
  M[i].h1ema50=iMA(M[i].name,PERIOD_H1,50,0,MODE_EMA,PRICE_CLOSE);
  M[i].h1macd=iMACD(M[i].name,PERIOD_H1,12,26,9,PRICE_CLOSE);
  M[i].h1adx=iADX(M[i].name,PERIOD_H1,14);
  M[i].h1rsi=iRSI(M[i].name,PERIOD_H1,14,PRICE_CLOSE);
  M[i].h1atr=iATR(M[i].name,PERIOD_H1,14);
  int handles[]={M[i].h4ema20,M[i].h4ema50,M[i].h4ema200,
    M[i].h4macd,M[i].h4adx,M[i].h4atr,M[i].h4rsi,
    M[i].h1ema20,M[i].h1ema50,M[i].h1macd,M[i].h1adx,M[i].h1rsi,M[i].h1atr};
  for(int j=0;j<ArraySize(handles);j++)
   if(handles[j]==INVALID_HANDLE)return INIT_FAILED;
  M[i].lastH4=0;M[i].lastH1=0;M[i].atrRelative=EMPTY_VALUE;
  M[i].state=ST_TRANSITION;M[i].selectedEngine="WAIT";M[i].lastSignal="WAIT";
  M[i].paperN=0;
 }
 EventSetTimer(InpTimerSeconds);
 update();
 Print("P9_V2_ROBUST_FIVE_SHADOW_INIT_OK: no CTrade / OrderSend / broker orders.");
 return INIT_SUCCEEDED;
}
void OnTimer(){ update(); }
void OnTick(){ /* no order execution, intentionally empty */ }
void OnDeinit(const int reason)
{
 EventKillTimer();
 for(int i=0;i<Count;i++)
 {
  IndicatorRelease(M[i].h4ema20);IndicatorRelease(M[i].h4ema50);
  IndicatorRelease(M[i].h4ema200);IndicatorRelease(M[i].h4macd);
  IndicatorRelease(M[i].h4adx);IndicatorRelease(M[i].h4atr);
  IndicatorRelease(M[i].h4rsi);IndicatorRelease(M[i].h1ema20);
  IndicatorRelease(M[i].h1ema50);IndicatorRelease(M[i].h1macd);
  IndicatorRelease(M[i].h1adx);IndicatorRelease(M[i].h1rsi);
  IndicatorRelease(M[i].h1atr);
 }
 Comment("");
}
