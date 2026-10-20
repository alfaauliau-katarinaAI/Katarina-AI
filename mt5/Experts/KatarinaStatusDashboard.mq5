#property strict
#property version "1.00"
#property description "Read-only Katarina owner monitor; no trading functions."
string prefix="KATARINA_STATUS_";
string source="Katarina\\owner-status.tsv";
void Label(const int row,const string text,const color tint=clrSilver)
{
 string name=prefix+IntegerToString(row);
 if(ObjectFind(0,name)<0)ObjectCreate(0,name,OBJ_LABEL,0,0,0);
 ObjectSetInteger(0,name,OBJPROP_CORNER,CORNER_LEFT_UPPER);
 ObjectSetInteger(0,name,OBJPROP_XDISTANCE,24);
 ObjectSetInteger(0,name,OBJPROP_YDISTANCE,32+row*23);
 ObjectSetInteger(0,name,OBJPROP_COLOR,tint);
 ObjectSetInteger(0,name,OBJPROP_FONTSIZE,row==0?12:10);
 ObjectSetString(0,name,OBJPROP_FONT,"Segoe UI");
 ObjectSetString(0,name,OBJPROP_TEXT,text);
 ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
}
void Paint()
{
 string bg=prefix+"BG";
 if(ObjectFind(0,bg)<0)ObjectCreate(0,bg,OBJ_RECTANGLE_LABEL,0,0,0);
 ObjectSetInteger(0,bg,OBJPROP_XDISTANCE,12);ObjectSetInteger(0,bg,OBJPROP_YDISTANCE,20);
 ObjectSetInteger(0,bg,OBJPROP_XSIZE,420);ObjectSetInteger(0,bg,OBJPROP_YSIZE,260);
 ObjectSetInteger(0,bg,OBJPROP_BGCOLOR,C'15,23,38');
 ObjectSetInteger(0,bg,OBJPROP_BORDER_TYPE,BORDER_FLAT);ObjectSetInteger(0,bg,OBJPROP_COLOR,C'45,68,90');
 ObjectSetInteger(0,bg,OBJPROP_SELECTABLE,false);
 Label(0,"KATARINA  /  DEMO",clrDeepSkyBlue);
 int f=FileOpen(source,FILE_READ|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
 string line="";if(f!=INVALID_HANDLE){line=FileReadString(f);FileClose(f);}
 string v[];int n=StringSplit(line,9,v);
 bool demo=AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO;
 bool terminal=TerminalInfoInteger(TERMINAL_CONNECTED)!=0;
 bool algo=TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)!=0;
 bool valid=n==17 && v[0]=="1";
 bool bound=valid && v[12]==IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) && v[13]==AccountInfoString(ACCOUNT_SERVER);
 long age=valid?(long)TimeGMT()-StringToInteger(v[1]):999999;
 bool fresh=valid && age>=-5 && age<=90;
 bool owner=valid && (v[3]=="OBSERVING" || v[3]=="WAITING" || v[3]=="STARTING");
 bool stopped=valid && v[14]=="1";
 bool executor=valid && v[16]=="1" && StringToInteger(v[15])<=90;
 string state=!valid?"BELUM TERHUBUNG":!demo?"AKUN BUKAN DEMO":!bound?"AKUN TIDAK SESUAI":!fresh?"HEARTBEAT TERPUTUS":stopped?"DIHENTIKAN PEMILIK":!owner?"PERLU DIPERIKSA":"TERHUBUNG";
 color tone=(valid && demo && bound && fresh && owner && !stopped)?clrMediumSpringGreen:clrOrange;
 Label(1,"Koneksi Katarina : "+state,tone);
 Label(2,"Akun : "+(demo?"DEMO":"BUKAN DEMO")+"  |  Broker : "+(terminal?"online":"offline"));
 Label(3,"Algo Trading : "+(algo?"ON":"OFF"),algo?clrMediumSpringGreen:clrOrange);
 Label(4,"Aktivitas : "+(valid?v[3]:"menunggu data"));
 Label(5,valid?"Worker : "+v[5]+"   |   Scan terakhir : "+v[6]+" instrumen":"Worker / scan : belum tersedia");
 Label(6,valid?"Demo : "+v[8]:"Demo : belum tersedia");
 Label(7,valid?"Keputusan entry : "+v[9]+"   |   Hasil selesai : "+v[10]:"Hasil : belum tersedia");
 Label(8,valid?"Dokter : "+v[11]+"   |   Siklus OK : "+v[4]:"Dokter : belum tersedia");
 Label(9,valid?"Heartbeat : "+IntegerToString(age)+" detik   |   Eksekutor : "+(executor?"terhubung":"belum segar"):"Menunggu heartbeat Python",fresh?clrSilver:clrOrange);
 // Local receipt proves this chart actually executed the monitor. No account IDs.
 int receipt=FileOpen("Katarina\\dashboard-receipt.txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON|FILE_SHARE_READ);
 if(receipt!=INVALID_HANDLE){FileWriteString(receipt,IntegerToString((long)TimeGMT())+"\t"+IntegerToString(ChartID())+"\t"+state+"\t"+(bound?"BOUND":"UNBOUND")+"\t"+IntegerToString(age));FileClose(receipt);}
 ChartRedraw();
}
int OnInit(){EventSetTimer(2);Paint();return INIT_SUCCEEDED;}
void OnTimer(){Paint();}
void OnDeinit(const int reason){EventKillTimer();ObjectsDeleteAll(0,prefix);}
