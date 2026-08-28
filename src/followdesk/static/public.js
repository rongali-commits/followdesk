const byId=id=>document.getElementById(id);
let config={};

async function loadConfig(){
  const response=await fetch('/api/config');
  config=await response.json();
  document.documentElement.style.setProperty('--primary',config.primary_color);
  document.documentElement.style.setProperty('--accent',config.accent_color);
  document.querySelectorAll('[data-logo]').forEach(el=>el.textContent=config.logo_text);
  document.querySelectorAll('[data-short-name]').forEach(el=>el.textContent=config.short_name);
  document.querySelectorAll('[data-business-name]').forEach(el=>el.textContent=config.name);
  byId('service').innerHTML='<option value="">Choose a service</option>'+config.service_options.map(item=>`<option>${escapeHtml(item)}</option>`).join('');
}

function escapeHtml(value){return String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));}

byId('leadForm').addEventListener('submit',async event=>{
  event.preventDefault();byId('formError').textContent='';byId('submitButton').disabled=true;byId('submitButton').textContent='Sending...';
  const data=new FormData(event.currentTarget);
  const payload={name:data.get('name'),email:data.get('email'),phone:'',company:'',service:data.get('service'),message:data.get('message'),source:'followdesk-demo',consent:data.get('consent')==='on',website:data.get('website')||''};
  try{
    const response=await fetch('/api/leads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const body=await response.json();
    if(!response.ok)throw new Error(Array.isArray(body.detail)?body.detail[0]?.msg:body.detail||'Could not submit your request.');
    byId('successMessage').textContent=body.message+' '+config.response_promise;
    byId('leadForm').hidden=true;byId('formSuccess').hidden=false;
    if(body.booking_url){byId('bookingLink').href=body.booking_url;}else{byId('bookingLink').hidden=true;}
  }catch(error){byId('formError').textContent=error.message;}
  finally{byId('submitButton').disabled=false;byId('submitButton').textContent='Send my request';}
});

loadConfig().catch(()=>{byId('formError').textContent='The form is temporarily unavailable. Please try again.';});
