import {useCallback,useEffect,useState} from 'react';
import {MessageCircle,Plus,Send,Trash2,LoaderCircle,MessagesSquare} from 'lucide-react';
import './chat.css';

type Lang='fa'|'en';
type Conversation={id:number;title:string;created:string;updated:string;message_count:number};
type Message={id:number;role:string;content:string;created:string};
const copy={
 fa:{title:'گفتگوهای من',new:'گفتگوی جدید',empty:'هنوز گفتگویی نداری',select:'یک گفتگو را انتخاب کن یا گفتگوی تازه‌ای بساز.',placeholder:'پیامت را اینجا بنویس...',send:'ارسال',loading:'در حال بارگذاری...',error:'خطا در ارتباط با سرور',saved:'پیام ذخیره شد؛ برای دریافت پاسخ هوش مصنوعی باید ارائه‌دهنده مدل پیکربندی شود.',notice:'زیرساخت گفتگو و ذخیره‌سازی فعال است. پاسخ‌گویی هوش مصنوعی پس از اتصال امن مدل فعال می‌شود.',delete:'حذف گفتگو',you:'شما',assistant:'دستیار'},
 en:{title:'My conversations',new:'New conversation',empty:'No conversations yet',select:'Choose a conversation or start a new one.',placeholder:'Write your message...',send:'Send',loading:'Loading...',error:'Could not connect to the server',saved:'Message saved. Configure a model provider to receive AI responses.',notice:'Chat storage is ready. AI responses will be enabled after a model is securely connected.',delete:'Delete conversation',you:'You',assistant:'Assistant'}
};
export default function ChatPanel({lang,token}:{lang:Lang;token?:string|null}){
 const t=copy[lang];const api=import.meta.env.VITE_API_URL?.replace(/\/$/,'');
 const [items,setItems]=useState<Conversation[]>([]);const [active,setActive]=useState<number|null>(null);const [messages,setMessages]=useState<Message[]>([]);const [draft,setDraft]=useState('');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 const headers={Authorization:'Bearer '+(token||''),'Content-Type':'application/json'};
 const load=useCallback(async()=>{if(!api||!token)return;setBusy(true);setError('');try{const r=await fetch(api+'/api/conversations',{headers});if(!r.ok)throw Error();const data:Conversation[]=await r.json();setItems(data);if(active&& !data.some(x=>x.id===active))setActive(null);}catch{setError(t.error)}finally{setBusy(false)}},[api,token,active,t.error]);
 useEffect(()=>{void load()},[load]);
 useEffect(()=>{if(!api||!token||!active){setMessages([]);return;}let live=true;fetch(api+'/api/conversations/'+active+'/messages',{headers}).then(async r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{if(live)setMessages(data)}).catch(()=>{if(live)setError(t.error)});return()=>{live=false}},[api,token,active]);
 async function create(){if(!api||!token)return;setBusy(true);setError('');try{const r=await fetch(api+'/api/conversations',{method:'POST',headers,body:JSON.stringify({title:lang==='fa'?'گفتگوی جدید':'New conversation'})});if(!r.ok)throw Error();const row:Conversation=await r.json();setItems(p=>[row,...p]);setActive(row.id);setMessages([]);setNotice('')}catch{setError(t.error)}finally{setBusy(false)}}
 async function send(e:React.FormEvent){e.preventDefault();const content=draft.trim();if(!content||!active||!api||!token||busy)return;setBusy(true);setError('');try{const r=await fetch(api+'/api/conversations/'+active+'/messages',{method:'POST',headers,body:JSON.stringify({content})});if(!r.ok)throw Error();const saved=await r.json();setMessages(p=>[...p,saved]);setDraft('');setNotice(t.saved);void load();}catch{setError(t.error)}finally{setBusy(false)}}
 async function remove(id:number){if(!api||!token)return;setBusy(true);try{const r=await fetch(api+'/api/conversations/'+id,{method:'DELETE',headers});if(!r.ok)throw Error();setItems(p=>p.filter(x=>x.id!==id));if(active===id)setActive(null)}catch{setError(t.error)}finally{setBusy(false)}}
 return <section className="chat-shell" aria-label={t.title}>
  <aside className="chat-list"><div className="chat-list-head"><h2>{t.title}</h2><button onClick={()=>void create()} disabled={busy} aria-label={t.new}><Plus size={18}/></button></div>
   {items.length===0&&!busy?<p className="chat-muted">{t.empty}</p>:items.map(item=><div className={'chat-item '+(active===item.id?'active':'')} key={item.id}><button className="chat-item-main" onClick={()=>setActive(item.id)}><MessageCircle size={17}/><span>{item.title}</span></button><button className="chat-remove" onClick={()=>void remove(item.id)} aria-label={t.delete}><Trash2 size={15}/></button></div>)}
  </aside>
  <div className="chat-room">{active===null?<div className="chat-welcome"><MessagesSquare size={42}/><h3>{t.select}</h3><button className="dash-create" onClick={()=>void create()} disabled={busy}><Plus size={17}/>{t.new}</button></div>:<><div className="chat-messages">{messages.length===0?<p className="chat-muted">{t.select}</p>:messages.map(m=><article className={'chat-bubble '+(m.role==='user'?'user':'assistant')} key={m.id}><small>{m.role==='user'?t.you:t.assistant}</small><p>{m.content}</p></article>)}</div><form className="chat-compose" onSubmit={send}><textarea value={draft} onChange={e=>setDraft(e.target.value)} placeholder={t.placeholder} maxLength={12000} rows={2}/><button className="dash-create" type="submit" disabled={busy||!draft.trim()} aria-label={t.send}>{busy?<LoaderCircle className="chat-spin" size={18}/>:<Send size={18}/>}</button></form></>}
   <p className="chat-notice">{notice||t.notice}</p>{error&&<p className="chat-error" role="alert">{error}</p>}
  </div>
 </section>
}
