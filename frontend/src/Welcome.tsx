import {useState} from 'react';
import {motion,useReducedMotion} from 'motion/react';
import {Check,Moon,Sun} from 'lucide-react';
type Props={theme:'light'|'dark';onToggleTheme:()=>void;onContinue:()=>void};
export default function Welcome({theme,onToggleTheme,onContinue}:Props){
 const [lang,setLang]=useState<'fa'|'en'>('fa');
 const reduced=useReducedMotion(); const fa=lang==='fa';
 return <main className="welcome-page" dir={fa?'rtl':'ltr'} lang={lang}>
  <button className="theme-toggle welcome-theme" onClick={onToggleTheme} aria-label={theme==='light'?'Enable dark mode':'Enable light mode'}>{theme==='light'?<Moon size={18}/>:<Sun size={18}/>}</button>
  <motion.section className="welcome-card glass" initial={reduced?false:{opacity:0,y:18}} animate={{opacity:1,y:0}} transition={{duration:.4}}>
   <div className="welcome-mark"><Check size={30}/></div><div className="welcome-brand">agentic.ai</div>
   <div className="welcome-language" role="group" aria-label="Language"><button className={fa?'selected':''} onClick={()=>setLang('fa')}>فارسی</button><button className={!fa?'selected':''} onClick={()=>setLang('en')}>English</button></div>
   <h1>{fa?'خوش آمدید':'Welcome'}</h1>
   <p>{fa?'حساب کاربری شما با موفقیت آماده شد. از فضای کاری خود لذت ببرید.':'Your account is ready. Welcome to your new workspace.'}</p>
   <button className="primary welcome-continue" onClick={onContinue}>{fa?'ورود به فضای کاری':'Go to workspace'} <span aria-hidden="true">→</span></button>
   <small>{fa?'همیشه می‌توانید زبان و تم را تغییر دهید.':'You can change the language and theme anytime.'}</small>
  </motion.section>
 </main>;
}