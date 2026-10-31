import { useEffect, useState } from 'react';
import { ShieldCheck, Cpu, UserCircle2, AlertCircle, Palette, RotateCcw } from 'lucide-react';

type Lang='fa'|'en';
type Capabilities={chat:boolean;agent_tasks:boolean};
type Palette={accent:string;background:string;surface:string;text:string};
const paletteKey='agentic-custom-palette';
const defaultPalette:Palette={accent:'#4988e7',background:'#eef5ff',surface:'#ffffff',text:'#263f60'};
const copy={
 fa:{account:'حساب کاربری',email:'ایمیل حساب',security:'امنیت',securityText:'رمز عبور به‌صورت هش در سرور ذخیره می‌شود. نشست فعلی با توکن Bearer مدیریت می‌شود.',provider:'وضعیت سرویس هوش مصنوعی',ready:'پیکربندی شده',missing:'نیازمند تنظیم کلید در سرور',loading:'در حال بررسی...',error:'وضعیت سرویس دریافت نشد.',note:'کلید API فقط باید در متغیر خصوصی سرور تنظیم شود؛ آن را در مرورگر یا مخزن قرار نده.',palette:'شخصی‌سازی ظاهر',paletteText:'رنگ اصلی، پس‌زمینه و سطح کارت‌ها را مطابق سلیقه‌ات انتخاب کن. تغییرات در همین مرورگر ذخیره می‌شوند.',accent:'رنگ اصلی',background:'پس‌زمینه',surface:'رنگ کارت‌ها',text:'رنگ متن',presets:'پالت‌های آماده',apply:'اعمال رنگ‌ها',reset:'بازنشانی',saved:'پالت ذخیره شد.'},
 en:{account:'Account',email:'Account email',security:'Security',securityText:'Passwords are hashed on the server. The current session uses a bearer token.',provider:'AI provider status',ready:'Configured',missing:'Server API key required',loading:'Checking...',error:'Could not load provider status.',note:'The API key must remain in a private server environment variable. Never put it in the browser or repository.',palette:'Appearance customization',paletteText:'Choose your accent, background, card and text colors. Your palette is saved in this browser.',accent:'Accent color',background:'Background',surface:'Card color',text:'Text color',presets:'Presets',apply:'Apply colors',reset:'Reset',saved:'Palette saved.'}
};
const presets:Record<string,Palette>={
 Ocean:{accent:'#4988e7',background:'#eef5ff',surface:'#ffffff',text:'#263f60'},
 Forest:{accent:'#27866d',background:'#edf7f1',surface:'#ffffff',text:'#234b3d'},
 Sunset:{accent:'#d66b55',background:'#fff3ed',surface:'#fffdfb',text:'#59372f'},
 Violet:{accent:'#8064d8',background:'#f4f0ff',surface:'#ffffff',text:'#3e345e'},
 Graphite:{accent:'#7b91aa',background:'#e9edf2',surface:'#f9fafb',text:'#293746'}
};
function readPalette():Palette{try{const value=JSON.parse(localStorage.getItem(paletteKey)||'null');if(value&&['accent','background','surface','text'].every(k=>typeof value[k]==='string'&&/^#[0-9a-fA-F]{6}$/.test(value[k])))return value}catch{}return defaultPalette}
function applyPalette(p:Palette){const root=document.documentElement;root.style.setProperty('--user-accent',p.accent);root.style.setProperty('--user-background',p.background);root.style.setProperty('--user-surface',p.surface);root.style.setProperty('--user-text',p.text);localStorage.setItem(paletteKey,JSON.stringify(p));window.dispatchEvent(new Event('agentic-palette-change'))}
export default function SettingsPanel({lang,email}:{lang:Lang;email?:string}) {
 const t=copy[lang],api=import.meta.env.VITE_API_URL?.replace(/\/$/,'');
 const [caps,setCaps]=useState<Capabilities|null>(null),[error,setError]=useState('');
 const [palette,setPalette]=useState<Palette>(readPalette),[saved,setSaved]=useState(false);
 useEffect(()=>{if(!api){setError(t.error);return}let alive=true;fetch(api+'/api/capabilities').then(async r=>{if(!r.ok)throw Error();return r.json()}).then(v=>{if(alive)setCaps(v)}).catch(()=>{if(alive)setError(t.error)});return()=>{alive=false}},[api,t.error]);
 function change(key:keyof Palette,value:string){setPalette(p=>({...p,[key]:value}));setSaved(false)}
 function save(){applyPalette(palette);setSaved(true)}
 function reset(){setPalette(defaultPalette);applyPalette(defaultPalette);setSaved(true)}
 return <section className="dash-panel settings-panel" dir={lang==='fa'?'rtl':'ltr'}>
  <div className="dash-project"><div className="dash-project-icon"><UserCircle2/></div><div className="dash-project-info"><strong>{t.account}</strong><small>{t.email}: {email||'—'}</small></div></div>
  <div className="dash-project"><div className="dash-project-icon"><ShieldCheck/></div><div className="dash-project-info"><strong>{t.security}</strong><small>{t.securityText}</small></div></div>
  <div className="dash-project"><div className="dash-project-icon"><Cpu/></div><div className="dash-project-info"><strong>{t.provider}</strong><small>{error||!caps?t.loading:(caps.chat&&caps.agent_tasks?t.ready:t.missing)}</small></div>{error&&<AlertCircle size={18}/>}</div>
  <section className="palette-settings">
   <div className="palette-heading"><span className="dash-project-icon"><Palette/></span><div><h2>{t.palette}</h2><p>{t.paletteText}</p></div></div>
   <div className="palette-grid">{(['accent','background','surface','text'] as const).map(key=><label className="palette-color" key={key}><span>{t[key]}</span><input type="color" value={palette[key]} onChange={e=>change(key,e.target.value)} /><code>{palette[key].toUpperCase()}</code></label>)}</div>
   <div className="palette-presets"><strong>{t.presets}</strong><div>{Object.entries(presets).map(([name,value])=><button type="button" key={name} className="palette-preset" onClick={()=>{setPalette(value);setSaved(false)}}><i style={{background:value.accent}}/><span>{name}</span></button>)}</div></div>
   <div className="palette-actions"><button type="button" className="dash-create" onClick={save}>{t.apply}</button><button type="button" className="palette-reset" onClick={reset}><RotateCcw size={16}/>{t.reset}</button>{saved&&<small role="status">{t.saved}</small>}</div>
  </section>
  <p className="dash-disclaimer">{t.note}</p>
 </section>;
}
