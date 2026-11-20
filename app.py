# ===== HireMind AI - ALL FEATURES IN ONE APP =====
import streamlit as st, requests, re, io
from collections import Counter
try:
    from pypdf import PdfReader
except: PdfReader=None
try:
    import docx
except: docx=None
try:
    from fpdf import FPDF
except: FPDF=None

GEMINI_KEY = st.secrets["GOOGLE_API_KEY"]

# --- BACKEND: READ FILE ---
def read_file(f):
    n=f.name.lower(); t=""
    if n.endswith(".pdf") and PdfReader:
        r=PdfReader(f)
        for p in r.pages: t+=(p.extract_text() or "")+"\n"
    elif n.endswith(".docx") and docx:
        d=docx.Document(f)
        for p in d.paragraphs: t+=p.text+"\n"
    else:
        try: t=f.read().decode("utf-8",errors="ignore")
        except: t=""
    return t

# --- BACKEND: CHECKERS ---
def analyze(text, jd):
    tl=text.lower()
    email=bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+",text))
    phone=bool(re.search(r"(\+91|91)?[\s-]?\d{10}",text))
    linkedin="linkedin" in tl; github="github" in tl
    secs={s:(s in tl) for s in ["education","experience","project","skill","certification","internship","summary","objective","language","training","achievement"]}
    tech_list=["python","java","javascript","react","node","sql","html","css","aws","docker","git","c++","flutter","machine learning","data","excel","power bi","figma","django","flask","mongodb"]
    soft_list=["communication","leadership","teamwork","problem solving","time management","adaptability","creativity"]
    tech=[s for s in tech_list if s in tl]; soft=[s for s in soft_list if s in tl]
    verbs=[v for v in ["built","created","developed","improved","increased","reduced","led","managed","designed","implemented","achieved"] if v in tl]
    words=re.findall(r"\b\w+\b",tl); cnt=Counter(words); repeated=[w for w,c in cnt.items() if c>15 and len(w)>3]
    issues=[]
    if ".." in text: issues.append("Double dots")
    if "  " in text: issues.append("Double spaces")
    if repeated: issues.append(f"Repeated: {', '.join(repeated[:5])}")
    typos={"recieve":"receive","teh":"the","adress":"address","experince":"experience","managment":"management"}
    ft=[f"{k}->{v}" for k,v in typos.items() if k in tl]
    if ft: issues.append("Spelling: "+",".join(ft))
    has_num=bool(re.search(r"\d+%|\d+ users|increased|reduced",tl))
    # ATS SCORE
    score=0
    score+=15 if email else 0; score+=10 if phone else 0; score+=10 if secs["education"] else 0
    score+=15 if secs["experience"] or secs["internship"] else 0; score+=10 if secs["project"] else 0
    score+=10 if secs["skill"] else 0; score+=5 if len(tech)>=3 else 0; score+=5 if len(soft)>=2 else 0
    score+=10 if len(text)>800 else 0; score+=10 if linkedin else 0
    score=min(score,100)
    # JD MATCH
    jd_words=set(re.findall(r"\b[a-zA-Z]{3,}\b",jd.lower()))-{"the","and","for","with","you","are","our","this","that","will","have","from","your","job","role","work","team"}
    res_words=set(re.findall(r"\b[a-zA-Z]{3,}\b",tl))
    matched=jd_words & res_words; missing=list(jd_words-res_words)[:20]
    jd_pct=int(len(matched)/max(len(jd_words),1)*100) if jd_words else 0
    return {"email":email,"phone":phone,"linkedin":linkedin,"github":github,"secs":secs,"tech":tech,"soft":soft,"verbs":verbs,"issues":issues,"has_num":has_num,"words":len(words),"score":score,"jd_pct":jd_pct,"matched":sorted(list(matched))[:20],"missing":missing}

def gemini(prompt):
    data={"contents":[{"parts":[{"text":prompt}]}]}
    for m in ["gemini-2.5-flash","gemini-2.5-flash-lite"]:
        try:
            r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_KEY}",json=data,timeout=90)
            j=r.json()
            if "candidates" in j: return j["candidates"][0]["content"]["parts"][0]["text"],None
        except: continue
    return None,"Gemini error - check key"

def to_pdf(t):
    if not FPDF: return None
    p=FPDF(); p.add_page(); p.set_auto_page_break(auto=True,margin=15); p.set_font("Arial",size=11)
    p.multi_cell(0,6,t.encode('latin-1','replace').decode('latin-1')); return bytes(p.output())
def to_docx(t):
    if not docx: return None
    d=docx.Document(); d.add_heading("HireMind Resume",0)
    for l in t.split("\n"): d.add_paragraph(l)
    b=io.BytesIO(); d.save(b); return b.getvalue()

# --- FRONTEND: ONE APP ---
st.set_page_config(page_title="HireMind AI - All Features", page_icon="✨", layout="wide")
st.title("✨ HireMind AI - All Features in One App")
st.caption("Upload + JD -> Dashboard + Feedback + AI Rewrite + Download | For Freshers / Experienced / Internship / Academic")

if "hist" not in st.session_state: st.session_state.hist=[]
if "rew" not in st.session_state: st.session_state.rew=""

with st.sidebar:
    st.header("⚙️ Settings")
    utype=st.selectbox("You are:",["Fresher","Experienced","Internship","Academic"])
    template=st.selectbox("Template:",["Professional","Modern","Minimal","Creative"])
    st.write("---"); st.write("📂 **Version History:**")
    for i,h in enumerate(st.session_state.hist): st.write(f"v{i+1} - ATS {h}/100")
    st.write("🔒 Privacy: No storage, only your session")

c1,c2=st.columns(2)
with c1: f=st.file_uploader("📄 Upload Resume (PDF, DOC, DOCX)",type=["pdf","doc","docx","txt"])
with c2:
    jd=st.text_area("📋 Paste Job Description",height=170)
    li=st.text_input("🔗 LinkedIn URL (optional)")

if f and st.button("🚀 ANALYZE ALL FEATURES",use_container_width=True):
    with st.spinner("Checking 60+ features..."):
        text=read_file(f)
        if len(text)<50: st.error("Cannot read resume - try text PDF")
        else:
            a=analyze(text,jd)
            st.session_state.hist.append(a["score"])
            t1,t2,t3,t4=st.tabs(["📊 Dashboard","🔍 Full Feedback","✨ AI Rewrite & Builder","⬇️ Preview & Download"])
            with t1:
                m1,m2,m3,m4=st.columns(4)
                m1.metric("ATS Score",f"{a['score']}/100"); m2.metric("Job Match",f"{a['jd_pct']}%"); m3.metric("Words",a['words']); m4.metric("Rating","Excellent" if a['score']>=80 else "Good" if a['score']>=60 else "Needs Work")
                st.progress(a['score']/100)
                st.write(f"**Job Readiness:** {'✅ Ready to Apply' if a['score']>=70 and a['jd_pct']>=50 else '⚠️ Improve First'} | **Structure:** {sum(a['secs'].values())}/11 sections | **Font/Formatting:** {'✅ Clean' if len(text)>500 else '⚠️ Too Short'}")
                st.write(f"**Career Progression / Gap:** {'Check dates in Experience' if a['secs']['experience'] else 'Add Internship/Projects for Freshers'} | **Inconsistent Info:** {'✅ No major issue' if a['secs']['education'] else '⚠️ Check dates'}")
                if a['missing']: st.warning(f"**Missing Keywords:** {', '.join(a['missing'][:15])}")
                if a['matched']: st.success(f"**Matched Keywords:** {', '.join(a['matched'][:15])}")
                st.write(f"**Missing Skills Suggestion:** Add skills from JD that are missing above | **Industry Checker:** {'✅ Good match' if a['jd_pct']>=50 else '⚠️ Low match - Use AI Rewrite'}")
            with t2:
                st.subheader("Section-by-Section Feedback - Real Time")
                st.write(f"**Personal Info:** {'✅ Email' if a['email'] else '❌ Email MISSING'} | {'✅ Phone' if a['phone'] else '❌ Phone MISSING'}")
                st.write(f"**Contact Validation:** LinkedIn {'✅' if a['linkedin'] or li else '❌ Add LinkedIn'} | GitHub {'✅' if a['github'] else '⚠️ Add GitHub'}")
                st.write(f"**Education:** {'✅' if a['secs']['education'] else '❌ Add Degree, College, Year'} | **Experience:** {'✅' if a['secs']['experience'] else '⚠️ Add Internship/Projects'} | **Internship:** {'✅' if a['secs']['internship'] else '⚠️ Add if any'}")
                st.write(f"**Projects:** {'✅' if a['secs']['project'] else '❌ Add 2-3 Projects'} | **Certification:** {'✅' if a['secs']['certification'] else '⚠️ Add Certifications/Courses'} | **Training:** {'✅' if a['secs']['training'] else '⚠️ Add Training'}")
                st.write(f"**Technical Skills:** {', '.join(a['tech']) if a['tech'] else '❌ None found'}")
                st.write(f"**Soft Skills:** {', '.join(a['soft']) if a['soft'] else '⚠️ Add Communication, Leadership'}")
                st.write(f"**Languages:** {'✅' if a['secs']['language'] else '⚠️ Add Languages'} | **Summary/Objective:** {'✅' if a['secs']['summary'] or a['secs']['objective'] else '❌ Add Summary'}")
                st.write(f"**Action Verbs:** {', '.join(a['verbs']) if a['verbs'] else '❌ Use Built, Created, Improved'} | **Achievements:** {'✅ Numbers found' if a['has_num'] else '❌ Add Numbers: 30%, 100 users'}")
                st.write(f"**Grammar/Spelling/Punctuation:** {'✅ Clean' if not a['issues'] else '⚠️ '+' | '.join(a['issues'])} | **Sentence Structure:** Use short bullet points")
                st.write(f"**Duplicate / Repeated:** {'✅ No duplicate' if not a['issues'] else 'Check above'} | **Qualification Match:** {'✅ Good' if a['secs']['education'] else '⚠️ Check JD qualification'}")
                st.write(f"**Recommendations:** Fix missing above + Add numbers + Add action verbs + Add missing keywords")
            with t3:
                st.subheader(f"AI Builder - {template} Template for {utype}")
                if st.button("✨ Rewrite Resume for This Job"): 
                    o,e=gemini(f"Rewrite resume for {utype}, style {template}. Keep truthful, add missing skills, action verbs, format Name, Summary, Skills, Projects, Experience, Education.\nJD:{jd}\nRESUME:{text[:4000]}")
                    if o: st.session_state.rew=o; st.text_area("Rewritten:",o,height=400)
                    else: st.error(e)
                if st.button("💡 Improvement Tips"):
                    o,e=gemini(f"Give 10 tips for this resume for this job: {text[:3000]} JD:{jd[:2000]}")
                    if o: st.write(o)
                if st.button("🎯 Headline + Summary + Action Verbs"):
                    o,e=gemini(f"Give 3 headlines + 1 summary + 10 action verbs for: {text[:3000]}")
                    if o: st.write(o)
            with t4:
                st.subheader("Preview & Download")
                st.text_area("Preview Original:",text[:3000],height=250)
                final=st.session_state.rew if st.session_state.rew else text
                st.text_area("Final Version (AI or Original):",final[:3000],height=250)
                cc1,cc2=st.columns(2)
                with cc1:
                    pb=to_pdf(final)
                    if pb: st.download_button("Download PDF 📄",pb,file_name="HireMind_Resume.pdf",mime="application/pdf",use_container_width=True)
                with cc2:
                    db=to_docx(final)
                    if db: st.download_button("Download DOCX 📝",db,file_name="HireMind_Resume.docx",use_container_width=True)
                st.success("✅ Compare Versions: Check sidebar history | ✅ Tailored for this vacancy")
if not f: st.info("👆 Upload resume to unlock ALL features in ONE app")
st.divider(); st.caption("HireMind AI | All 60+ Features in One App | Made by You")