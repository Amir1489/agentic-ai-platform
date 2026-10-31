import { useEffect, useState } from 'react';
import { ShieldCheck, Cpu, UserCircle2, AlertCircle } from 'lucide-react';

type Lang='fa'|'en';
type Capabilities={chat:boolean;agent_tasks:boolean};
const copy={fa:{account:'حساب کاربری',email:'ایمیل حساب',security:'امنیت',securityText:'رمز عبور به‌صورت هش در سرور ذخیره می‌شود. نشست فعلی با توکن Bearer مدیریت می‌شود.',provider:'وضعیت سرویس هوش مصنوعی',ready:'پیکربندی شده',missing:'نیازمند تنظیم کلید در سرور',loading:'در حال بررسی...',error:'وضعیت سرویس دریافت نشد.',note:'کلید API فقط باید در متغیر خصوصی سرور تنظیم شود؛ آن را در مرورگر یا مخزن قرار نده.'},en:{account:'Account',email:'Account email',security:'Security',securityText:'Passwords are hashed on the server. The current session uses a bearer token.',provider:'AI provider status',ready:'Configured',missing:'Server API key required',loading:'Checking...',error:'Could not load provider status.',note:'The API key must remain in a private server environment variable. Never put it in the browser or repository.'}};
export default function SettingsPanel({lang,email}:{lang:Lang;email?:string}) {
 const t=copy[lang],api=import.meta.env.VITE_API_URL?.replace(/\/$/,'');
 const [caps,setCaps]=useState<Capabilities|null>(null),[error,setError]=useState('');
 useEffect(()=>{if(!api){setError(t.error);return}let alive=true;fetch(api+'/api/capabilities').then(async r=>{if(!r.ok)throw Error();return r.json()}).then(v=>{if(alive)setCaps(v)}).catch(()=>{if(alive)setError(t.error)});return()=>{alive=false}},[api,t.error]);
 return <section className="dash-panel" dir={lang==='fa'?'rtl':'ltr'}>
  <div className="dash-project"><div className="dash-project-icon"><UserCircle2/></div><div className="dash-project-info"><strong>{t.account}</strong><small>{t.email}: {email||'—'}</small></div></div>
  <div className="dash-project"><div className="dash-project-icon"><ShieldCheck/></div><div className="dash-project-info"><strong>{t.security}</strong><small>{t.securityText}</small></div></div>
  <div className="dash-project"><div className="dash-project-icon"><Cpu/></div><div className="dash-project-info"><strong>{t.provider}</strong><small>{error||!caps?t.loading:(caps.chat&&caps.agent_tasks?t.ready:t.missing)}</small></div>{error&&<AlertCircle size={18}/>}</div>
  <p className="dash-disclaimer">{t.note}</p>
 </section>;
}
