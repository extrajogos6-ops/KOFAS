const portablePrefs=Object.assign(Object.create(null),__PREFS__);
function installPortablePreferences(ga,h) {
 const match=h.signature.match(/\b([A-Za-z0-9_]+)\((.*)\)/);if(!match)return false;
 const name=match[1],count=match[2].trim()?match[2].split(',').length:0;
 const stringNew=new NativeFunction(ga.getExportByName('il2cpp_string_new'),'pointer',['pointer']);
 const pin=new NativeFunction(ga.getExportByName('il2cpp_gchandle_new'),'uint32',['pointer','bool']);
 const strings=new Map();
 function managed(value){value=String(value??'');if(!strings.has(value)){const p=stringNew(Memory.allocUtf8String(value));pin(p,1);strings.set(value,p);}return strings.get(value);}
 function changed(op,key,value){send({event:'portable-pref',op,key,value});}
 let callback,ret,args;
 if(/^(Set|TrySet)(Int|Float|String)$/.test(name)||name==='TrySetSetString') {
  const kind=name.endsWith('Int')?'int':name.endsWith('Float')?'float':'pointer';
  ret=name.startsWith('Try')?'bool':'void';args=['pointer',kind,'pointer'];
  callback=function(key,value){key=text(key);value=kind==='pointer'?text(value):value;portablePrefs[key]=value;changed('set',key,value);return 1;};
 } else if(/^Get(Int|Float|String)$/.test(name)) {
  const kind=name==='GetInt'?'int':name==='GetFloat'?'float':'pointer';ret=kind;args=count===2?['pointer',kind,'pointer']:['pointer','pointer'];
  callback=function(key,fallback){key=text(key);if(Object.prototype.hasOwnProperty.call(portablePrefs,key)){const value=portablePrefs[key];return kind==='pointer'?managed(value):Number(value)||0;}return count===2?fallback:kind==='pointer'?managed(''):0;};
 } else if(name==='HasKey') {ret='bool';args=['pointer','pointer'];callback=function(key){return Object.prototype.hasOwnProperty.call(portablePrefs,text(key))?1:0;};
 } else if(name==='DeleteKey') {ret='void';args=['pointer','pointer'];callback=function(key){key=text(key);delete portablePrefs[key];changed('delete',key,null);};
 } else if(name==='DeleteAll') {ret='void';args=['pointer'];callback=function(){for(const k of Object.keys(portablePrefs))delete portablePrefs[k];changed('clear',null,null);};
 } else if(name==='Save') {ret='void';args=['pointer'];callback=function(){};
 } else return false;
 Interceptor.replace(ga.base.add(h.rva),new NativeCallback(callback,ret,args));return true;
}

'use strict';
const hooks = __HOOKS__;
function text(p) { try { const n=p.add(16).readS32();return n>=0&&n<8000?p.add(20).readUtf16String(n):null; } catch (_) {return null;} }
const hooked=new Set();
function observeModule(module) {
 if(module.name.toLowerCase()==='advapi32.dll') {
  for(const name of ['RegCreateKeyExW','RegOpenKeyExW']) {const p=module.findExportByName(name);if(!p)continue;
   Interceptor.attach(p,{onEnter(a){try{const path=a[1].readUtf16String();if(path&&path.includes('KOF ALLSTAR')){a[1]=Memory.allocUtf16String(path.replaceAll('KOF ALLSTAR','KOFAS117DEV'));this.keep=a[1];send({event:'registry-profile-isolated'});}}catch(_){}}});
  }
 }
 if(module.name.toLowerCase()!=='gameassembly.dll'||hooked.has(module.name))return;
 hooked.add(module.name);send({event:'gameassembly-loaded',base:module.base.toString()});
 setTimeout(function enableBackground(){try{const domain=new NativeFunction(module.getExportByName('il2cpp_domain_get'),'pointer',[])();if(domain.isNull()){setTimeout(enableBackground,100);return;}
  new NativeFunction(module.getExportByName('il2cpp_thread_attach'),'pointer',['pointer'])(domain);
  const p=new NativeFunction(module.getExportByName('il2cpp_resolve_icall'),'pointer',['pointer'])(Memory.allocUtf8String('UnityEngine.Application::set_runInBackground(System.Boolean)'));
  if(!p.isNull()){new NativeFunction(p,'void',['bool'])(1);send({event:'background-enabled'});if(__MUTE__){const mute=new NativeFunction(module.getExportByName('il2cpp_resolve_icall'),'pointer',['pointer'])(Memory.allocUtf8String('UnityEngine.AudioListener::set_volume(System.Single)'));if(!mute.isNull())new NativeFunction(mute,'void',['float'])(0);}}
 }catch(e){send({event:'background-error',message:String(e)});}},1000);
 // This archived build enters the manifest error-dialog coroutine even when
 // its own native loader succeeds. UI does not exist yet at that point.
 // Only advance to the original registration state after native validation.
 const loadPlatform=new NativeFunction(module.base.add(0x163a950),'bool',['pointer','pointer','pointer','pointer','pointer']);
 Interceptor.attach(module.base.add(0x164a510),{onEnter(a){const it=a[0];if(it.add(0x10).readS32()!==0)return;
  const ok=loadPlatform(it.add(0x20).readPointer(),it.add(0x38),it.add(0x40),it.add(0x48),ptr(0));
  if(ok&&!it.add(0x40).readPointer().isNull()&&!it.add(0x48).readPointer().isNull()){
   it.add(0x28).writeU32(it.add(0x28).readU32()&0xfffffffe);it.add(0x10).writeS32(2);
   send({event:'native-manifest-validated'});
  }else send({event:'native-manifest-rejected'});
 }});
 // Complete the overlay only after native lobby initialization/renewal is ready.
 const getUi=new NativeFunction(module.base.add(0x18e8ce0),'pointer',['pointer']);
 const showLoading=new NativeFunction(module.base.add(0x18ec670),'void',['pointer','bool','bool','int','pointer']);
 const getClassName=new NativeFunction(module.getExportByName('il2cpp_class_get_name'),'pointer',['pointer']);
 let completedLobby=null;
 Interceptor.attach(module.base.add(0x1700ce0),{onEnter(a){this.manager=a[0];},onLeave(){
  const manager=this.manager,scene=manager.add(0x28).readPointer();if(scene.isNull())return;
  if(getClassName(scene.readPointer()).readUtf8String()!=='SceneLobby_Lobby'){completedLobby=null;return;}
  if(completedLobby===scene.toString()||manager.add(0x49).readU8()||!scene.add(0x41).readU8()||scene.add(0x30).readPointer().isNull())return;
  const ui=getUi(ptr(0));if(ui.isNull()||ui.add(0x13d).readU8()||ui.add(0x13c).readU8())return;
  completedLobby=scene.toString();showLoading(ui,0,0,0,ptr(0));send({event:'lobby-transition-completed'});
 }});
 const formatException=module.findExportByName('il2cpp_format_exception');
 const raise=module.findExportByName('il2cpp_raise_exception');
 if(formatException&&raise){const format=new NativeFunction(formatException,'void',['pointer','pointer','int']);Interceptor.attach(raise,{onEnter(a){try{const out=Memory.alloc(4096);format(a[0],out,4096);send({event:'managed-exception',message:out.readUtf8String()});}catch(_){}}});}
 for(const h of hooks) {
  if(h.class==='UnityEngine.PlayerPrefs'){installPortablePreferences(module,h);continue;}
  if(h.class==='Netmarble.CrashReporter.Util.DataManager'&&/SetAndGetRequiredCacheDirectory/.test(h.signature)) {
   let path=null;Interceptor.replace(module.base.add(h.rva),new NativeCallback(function(){
    if(path===null){path=new NativeFunction(module.getExportByName('il2cpp_string_new'),'pointer',['pointer'])(Memory.allocUtf8String(__CACHE__));new NativeFunction(module.getExportByName('il2cpp_gchandle_new'),'uint32',['pointer','bool'])(path,1);}
    send({event:'crash-cache-isolated'});return path;
   },'pointer',['pointer']));continue;
  }
  if(h.class.startsWith('Netmarble.CrashReporter.')&&/ Initialize\(/.test(h.signature)) {
   Interceptor.replace(module.base.add(h.rva),new NativeCallback(function(){send({event:'crash-reporter-disabled',rva:h.rva});},'void',['pointer','pointer','pointer','pointer']));continue;
  }
  if(h.class==='NMSSSA.SecurityManager'&&/DetectApkIntgError/.test(h.signature)) {
   Interceptor.replace(module.base.add(h.rva),new NativeCallback(function(){send({event:'local-integrity-handler-disabled',rva:h.rva});},'void',['pointer','bool','bool','pointer']));continue;
  }
  try {Interceptor.attach(module.base.add(h.rva),{onEnter(a){
   this.label=h.class+'.'+h.signature;
   const msg={event:'enter',method:this.label};
   if(h.class==='UIPopup_NetworkError') {msg.error=text(a[0]);msg.state=a[0].toInt32();if(h.signature.includes('ShowNetworkErrorMessage')){msg.reason=text(a[1].add(8).readPointer());msg.detail=a[1].add(4).readS32();msg.stack=Thread.backtrace(this.context,Backtracer.ACCURATE).filter(p=>p.compare(module.base)>=0&&p.compare(module.base.add(module.size))<0).map(p=>p.sub(module.base).toString());}}
   if(h.class==='AssetBundleLoader'){this.loader=a[0];msg.bundle=text(a[1]);}
   if(h.class==='AssetBundleDownloader') {msg.error=text(a[2]);msg.url=text(a[0].add(0x50).readPointer());}
   if(h.class==='AssetBundleManager'&&/void (LoadSnapshotInfo|LoadRemoteBundleInfo)\(/.test(h.signature)){msg.url=text(a[1].add(0x50).readPointer());msg.downloadError=a[1].add(0x44).readS32();msg.error=text(a[1].add(0x48).readPointer());}
   if(/SendPacketJson|SendPacketProto/.test(h.signature))msg.route=text(a[1]);
   if(/RecvDownloadSecuredConfig|ConfigLoadFailed|DecryptAndLoadTable|SetHashToTable/.test(h.signature))msg.args=[a[0].toString(),a[1].toString(),a[2].toString()];
   send(msg);
  },onLeave(r){if(this.loader)send({event:'loader-result',method:this.label,state:this.loader.add(16).readS32(),bundle:text(this.loader.add(32).readPointer())});if(/InitializeSDK|IsAuthenticated|DecryptAndLoadTable|ParseConfigServerInfo/.test(h.signature))send({event:'leave',method:this.label,result:r.toString()});}});
  } catch(e){send({event:'hook-error',method:h.class+'.'+h.signature,error:String(e)});}
 }
}
const moduleObserver=Process.attachModuleObserver({onAdded:observeModule});
const ensureGameAssembly=setInterval(()=>{const ga=Process.findModuleByName("GameAssembly.dll");if(ga){observeModule(ga);clearInterval(ensureGameAssembly);}},100);
send({event:'probe-ready'});
