function toggleProfile(){
  let d=document.getElementById('profileDrop');
  d.style.display = d.style.display==='none' ? 'block' : 'none';
  let b=document.getElementById('notifDrop');
  if(b) b.style.display='none';
}
function toggleBell(){
  let d=document.getElementById('notifDrop');
  d.style.display = d.style.display==='none' ? 'block' : 'none';
  let p=document.getElementById('profileDrop');
  if(p) p.style.display='none';
}
document.addEventListener('click', function(e){
  let pb=document.getElementById('profileBtn');
  let pd=document.getElementById('profileDrop');
  let bb=document.getElementById('bellBtn');
  let nd=document.getElementById('notifDrop');
  if(pb && pd && !pb.contains(e.target) && !pd.contains(e.target)){
    pd.style.display='none';
  }
  if(bb && nd && !bb.contains(e.target) && !nd.contains(e.target)){
    nd.style.display='none';
  }
});

function showToast(message, type='success'){
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  
  // GREEN for success, RED for error
  const bg = type === 'success' 
    ? 'background:#16a34a; border:1px solid #15803d;' 
    : 'background:#dc2626; border:1px solid #991b1b;';

  t.style.cssText = `
    ${bg}
    color:white;
    padding:12px 14px;
    border-radius:12px;
    box-shadow:0 8px 24px rgba(0,0,0,0.2);
    display:flex;
    align-items:center;
    gap:10px;
    font-size:13px;
    font-weight:600;
    margin-bottom:8px;
    transition:all .3s ease;
    pointer-events:auto;
  `;
  t.className = `toast ${type}`;

  const icon = type==='success' 
    ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" fill="white" fill-opacity="0.25"/><path d="M7.5 12.5L10.5 15.5L16.5 9.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`
    : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" fill="white" fill-opacity="0.25"/><path d="M9 9L15 15M15 9L9 15" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>`;
  
  t.innerHTML = `
    <span style="display:flex;align-items:center">${icon}</span>
    <span style="flex:1;line-height:1.3">${message}</span>
    <span onclick="this.parentElement.remove()" style="opacity:.7;cursor:pointer;padding:2px 6px;background:rgba(255,255,255,0.2);border-radius:6px">✕</span>
  `;
  
  c.appendChild(t);
  
  setTimeout(()=>{ 
    t.style.opacity='0'; 
    t.style.transform='translateX(100%)'; 
    setTimeout(()=>t.remove(),300)
  }, 4000);
}
