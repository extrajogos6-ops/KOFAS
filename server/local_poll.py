"""Local poll. DownloadScheduleList feeds the client's OpsRepository: an OperateSchedule with Category 2 goes to
OpsRepository.HandleDungeonSchedules, keyed by SubCategory = EDungeonType (2 Growth, 4 SoulQuest = Fighter Quest, 5 EpicQuest, 6 TeamRelay) and
Index = the table schedule/content index; Detail.OffOnSched: 0 DISABLE, 1 ALWAYS, 2 TIME_SCHEDULE (OpsDefines); Detail.StartTs/EndTs are seconds (OpsRepository.StartTimeSeconds).
Without these the EVENT (SPQuest) screen lists nothing and crashes in UIPage_SPQuestModeSelect.CallbackScrollFinish.
Field names are verbatim from the Android dump (OperateSchedule / OperateScheduleData)."""
import json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def _sched(sub,index):
    return {'Version':1,'Category':2,'SubCategory':sub,'Index':index,'Custom':'','TagList':[],
            'Detail':{'SubGroup':[],'OffOnSched':1,'Weekly':[],'Hourly':[],'StartTs':1600000000,'EndTs':4102444800,
                      'Offset':0,'estimatedTime':0}}

def month_end_s():
    """Start of next local calendar month, epoch seconds (rolling monthly event window)."""
    t = time.localtime()
    return int(time.mktime((t.tm_year + (t.tm_mon == 12), t.tm_mon % 12 + 1, 1, 0, 0, 0, 0, 0, -1)))

def week_start():
    """Monday 00:00 local time of the current week, epoch seconds (Time Attack season = one week)."""
    t = time.localtime()
    return int(time.mktime((t.tm_year, t.tm_mon, t.tm_mday - t.tm_wday, 0, 0, 0, 0, 0, -1)))

def download_schedules():
    def load(n):
        p=ROOT/n
        return json.loads(p.read_text()) if p.exists() else None
    out=[]
    qe=load('questevent.json')
    for e in (qe or {}).get('events',[]):
        for sub in e.get('dungeon',[2]):
            x=_sched(sub,int(e.get('schedule',5001)))
            # Descended page (UIPage_EventMain.SetEventGroupList): open EDungeonType 3 schedules by Index, kept only if
            # TagList contains 1; Index = QuestEventScheduleTable index
            if sub==3: x['TagList']=[1]
            out.append(x)
    mr=load('marathon.json')
    for m in (mr or {}).get('marathons',[]):   # Marathon: STORY hub cards. DungeonController.OpenMarathonList = open EDungeonType 3
        # schedules whose TagList holds 11 (Controller_CampaignSelector.GetMarathonList); Index = QuestEventSchedule index
        x=_sched(3,int(m['schedule'])); x['TagList']=[11]; out.append(x)
    tw=load('eventtower.json')
    for t in (tw or {}).get('towers',[]):   # Event Towers: QuestEventTable.GetOpendEventTowerList needs the schedule open (sub 3);
        out.append(_sched(3,int(t['schedule'])))   # no tag: the Descended page (TagList 1) and Marathon list (11) skip it
    sm=load('smash.json')
    for e in (sm or {}).get('events',[]):   # Smash ('Rush') events: STORY hub cards (Controller_CampaignSelector.GetSmashList ->
        x=_sched(3,int(e['schedule'])); x['TagList']=[1]; out.append(x)   # DungeonController.OpenSmashIndex: open sub 3, TagList 1, subType 43)
    ep=load('epicquest.json')
    for e in (ep or {}).get('epics',[]): out.append(_sched(5,int(e['index'])))   # Epic Quest: one EDungeonType 5 schedule per episode
    fq=load('fighterquest.json')
    if fq and fq.get('pickup'):   # SoulQuest (Fighter Quest) pickup: SubGroup = fighters with duels (OpsRepository.OpenPickupFighters)
        s=_sched(4,1); s['Detail']['SubGroup']=list(fq['pickup']); out.append(s)
    inf=load('infinite.json')
    if inf:   # Infinite Fight: InfiniteFightEventProto.get_Schedule = OpsRepository.Get(15, eventIndex)
        s=_sched(0,int(inf['event'])); s['Category']=15
        t=time.localtime()   # season = local calendar month, same as the server's league_season() SeasonEndTime
        s['Detail']['StartTs']=int(time.mktime((t.tm_year,t.tm_mon,1,0,0,0,0,0,-1)))
        s['Detail']['EndTs']=int(time.mktime((t.tm_year+(t.tm_mon==12),t.tm_mon%12+1,1,0,0,0,0,0,-1))); out.append(s)
    ao=load('allout.json')
    if ao:   # All Out Fight: AllOutFightEventProto.get_Schedule = OpsRepository.Get(28, eventIndex); season = calendar month
        s=_sched(0,int(ao['event'])); s['Category']=28
        t=time.localtime()
        s['Detail']['StartTs']=int(time.mktime((t.tm_year,t.tm_mon,1,0,0,0,0,0,-1)))
        s['Detail']['EndTs']=int(time.mktime((t.tm_year+(t.tm_mon==12),t.tm_mon%12+1,1,0,0,0,0,0,-1))); out.append(s)
    tr=load('teamrelay.json')
    if tr: out.extend(_sched(6,int(r['index'])) for r in [tr]+list(tr.get('relays') or []))   # Team Relay + High Score / Meta relays
    ch=load('challenge.json')
    if ch:   # Challenge: ChallengeScheduleProto.get_Schedule = OpsRepository.Get(12, scheduleIndex) (dates; IsOpenEventTime)
        for sc in ch.get('schedules') or [{'schedule':ch['schedule']}]:   # one card per Time Attack stage (2026-10-23)
            s=_sched(0,int(sc['schedule'])); s['Category']=12
            # weekly season: ChallengeScheduleProto.get_EndDate = this schedule's EndTs ('Ends in' on the card)
            w=week_start(); s['Detail']['StartTs']=w; s['Detail']['EndTs']=w+7*86400; out.append(s)
    gr=load('guildraid.json')
    if gr:   # Guild Raid boss groups: DungeonController.GetDungeonSchedule(8, group) (selector remaining time)
        for g in gr.get('groups',{}): out.append(_sched(8,int(g)))
    dp=load('dispatch.json')
    if dp:   # Dispatch: DispatchManager.IsDispatchOpen = OpsRepository.Get(30, dispatchMainIndex) (lobby Dispatch button)
        s=_sched(0,int(dp['main'])); s['Category']=30; out.append(s)
    cr=load('craft.json')
    if cr:   # Craft: CraftController.IsOpenCraft = an OpsRepository category 11 schedule whose SubGroup holds the craft index
        s=_sched(0,1); s['Category']=11; s['Detail']['SubGroup']=sorted(int(k) for k in cr); out.append(s)
    bg=load('bingo.json')
    if bg:   # Bingo: GetEventSchedule(3, bingoGroup); window = this calendar month like the board's expireTime (local_player
        # bingo_info month_end_ms) - the 2100 default showed '26731d' on the lobby icon (2026-10-24)
        s=_sched(3,int(bg['group'])); s['Category']=4; t=time.localtime()
        s['Detail']['StartTs']=int(time.mktime((t.tm_year,t.tm_mon,1,0,0,0,0,0,-1))); s['Detail']['EndTs']=month_end_s(); out.append(s)
    for name,typ in (('luckychance.json',4),('dice.json',2),('eventpagemission.json',5),('eventbook.json',7),('giftevent.json',9),('teamevent.json',8)):   # common events: CommonEventController.GetEventSchedule(type, index) =
        ev=load(name)                                 # Category 4, SubCategory = type, Index = event index
        if ev:
            s=_sched(typ,int(ev['index'])); s['Category']=4; out.append(s)   # rolling monthly; Team Event = weekly season
            s['Detail']['EndTs']=week_start()+7*86400 if typ==8 else month_end_s()
    mt=load('memtrade.json')   # Memory Dimension Trade: one Category 29 schedule per MemoryCategoryTable row (UIUnit_MemoryExchange)
    for k in sorted(mt or {}, key=int):
        s=_sched(0,int(k)); s['Category']=29; s['Detail']['EndTs']=month_end_s(); out.append(s)
    ec=load('eventcraft.json')   # Event Craft: Category 4 / SubCategory 6, Detail.SubGroup holds the craft event index
    if ec: s=_sched(6,int(ec['index'])); s['Category']=4; s['Detail']['SubGroup']=[int(ec['index'])]; s['Detail']['EndTs']=month_end_s(); out.append(s)
    ca=load('carnival.json')   # Carnival: CarnivalScheduleController reads Category 25, Index = carnivalIndex
    if ca: s=_sched(0,int(ca['index'])); s['Category']=25; s['Detail']['EndTs']=month_end_s(); out.append(s)
    ro=load('roulette.json')
    if ro:   # Roulette: RouletteManager.GetSchedule = OpsRepository.GetScheduleByCategorySubGroup(23, rouletteIndex)
        s=_sched(0,int(ro['index'])); s['Category']=23; s['Detail']['SubGroup']=[int(ro['index'])]; out.append(s)
    return out

def poll_safe(payload):
    """poll() for a request it would refuse: the fields it checks are reset to their defaults instead of raising, so the
    client still gets its DownloadScheduleList. The first poll after sign-in carries the schedules; when it got a 400
    (2026-10-25, sporadic, cause not seen) the client had no schedules for the whole session and the guild raid boss
    selector showed only Omega (NullReferenceException in UIUnit_GuildDungeonSelector.SetRemainTime)."""
    p=dict(payload) if isinstance(payload,dict) else {}
    tick=p.get('ClientTick',0)
    if not isinstance(tick,int) or isinstance(tick,bool) or not -(1<<63)<=tick<(1<<63):
        try: tick=int(float(tick))
        except (TypeError,ValueError,OverflowError): tick=0
        p['ClientTick']=tick if -(1<<63)<=tick<(1<<63) else 0
    if not isinstance(p.get('PollCateg',''),str) or len(p.get('PollCateg',''))>512: p['PollCateg']=''
    if not isinstance(p.get('PollHash',''),str) or len(p.get('PollHash',''))>1024: p['PollHash']=''
    v=p.get('PollDatas',[])
    if not isinstance(v,list) or len(v)>1024 or any(not isinstance(x,int) or isinstance(x,bool) or not -(1<<31)<=x<(1<<31) for x in v):
        p['PollDatas']=[]
    return poll(p)


def poll(payload):
    tick=payload.get('ClientTick',0)
    category=payload.get('PollCateg','')
    poll_hash=payload.get('PollHash','')
    values=payload.get('PollDatas',[])
    if not isinstance(tick,int) or isinstance(tick,bool) or not -(1<<63)<=tick<(1<<63):
        raise ValueError('invalid_client_tick')
    if not isinstance(category,str) or len(category)>512 or not isinstance(poll_hash,str) or len(poll_hash)>1024:
        raise ValueError('invalid_poll_text')
    if not isinstance(values,list) or len(values)>1024 or any(not isinstance(v,int) or isinstance(v,bool) or not -(1<<31)<=v<(1<<31) for v in values):
        raise ValueError('invalid_poll_values')
    return {'ResultCode':0,'ResultMessage':'','DownloadScheduleList':download_schedules(),
            'gachaRateUpScheduleList':[],'OptionalData':'','ApiCall':'',
            'PollHash':'local-dungeon-schedule-v19-%d'%week_start(),'ClientTick':tick,
            'ServerTime':int(time.time()*1000)}
