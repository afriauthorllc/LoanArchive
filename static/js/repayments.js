const CSRF = "{{ csrf_token }}";
const CHECK_BOOK_URL = "{% url 'loans:check_book_number' %}";
const BULK_URL = "{% url 'loans:bulk_repayment_submit' %}";

function showToast(message, type='success'){
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  
  const iconSvg = type === 'success'
    ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1e4a8a" stroke-width="1.8"><circle cx="12" cy="12" r="9.5" stroke-opacity="0.15" fill="#f0f7ff"/><path d="M8.5 12.5L11 15L15.5 9.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
    : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="9.5" stroke="#ef4444" stroke-opacity="0.15" fill="#fef2f2"/><path d="M9 9L15 15M15 9L9 15" stroke-linecap="round"/></svg>`;

  t.innerHTML = `<span style="display:flex">${iconSvg}</span><span style="flex:1">${message}</span><span onclick="this.parentElement.remove()" style="opacity:.7;cursor:pointer;margin-left:8px">✕</span>`;
  c.appendChild(t);
  setTimeout(()=>{ t.style.opacity='0'; t.style.transform='translateX(100%)'; setTimeout(()=>t.remove(),300)}, 4000);
}
function getBookStatus(book){
  return fetch(`${CHECK_BOOK_URL}?book_number=${encodeURIComponent(book)}`).then(r=>r.json());
}
function updateCount(){
  let c=0; document.querySelectorAll('#repayTable tbody tr[data-loan-id]').forEach(tr=>{
    const b=tr.querySelector('.book-field')?.value.trim(); const a=tr.querySelector('.amount-field')?.value.trim(); if(b&&a) c++;
  });
  document.getElementById('countText').textContent=c+' entered';
  const btn = document.getElementById('confirmBtn');
  btn.disabled=c===0;
  btn.textContent=c===0?'Confirm Payments':`Confirm ${c} Payments`;
}
document.querySelectorAll('.book-field').forEach(inp=>{
  inp.addEventListener('blur', async function(){
    const val=this.value.trim(); if(!val) return;
    try{
      const res=await getBookStatus(val);
      const err=this.parentElement.querySelector('.row-error');
      if(res.exists){ this.classList.add('is-invalid'); this.classList.remove('is-valid'); err.textContent='Book #'+val+' already used!'; err.style.display='block'; }
      else { this.classList.remove('is-invalid'); this.classList.add('is-valid'); err.style.display='none'; }
    }catch(e){}
  });
  inp.addEventListener('input', updateCount);
});
document.querySelectorAll('.amount-field').forEach(i=>i.addEventListener('input', updateCount));

document.querySelectorAll('.filter-row input[data-col]').forEach(inp=>{
  inp.addEventListener('input', function(){
    const col=this.dataset.col; const val=this.value.toLowerCase();
    document.querySelectorAll('#repayTable tbody tr[data-loan-id]').forEach(tr=>{
      let txt=''; if(col==='client') txt=tr.dataset.client||''; if(col==='loan') txt=tr.dataset.loan||''; if(col==='date') txt=tr.cells[5]?.innerText||''; if(col==='status') txt=tr.cells[6]?.innerText||'';
      tr.style.display=val===''||txt.toLowerCase().includes(val)?'':'none';
    });
  });
});

function openModal(){
  let html=''; let total=0; let count=0;
  document.querySelectorAll('#repayTable tbody tr[data-loan-id]').forEach(tr=>{
    const book=tr.querySelector('.book-field')?.value.trim(); const amount=tr.querySelector('.amount-field')?.value.trim();
    if(book&&amount){ count++; total+=parseInt(amount)||0; html+=`<div class="modal-item"><div><div style="font-weight:700">${tr.dataset.client}</div><div style="font-size:12px;color:#6b7280">Book #${book} • ${tr.dataset.loan}</div></div><strong>UGX ${parseInt(amount).toLocaleString()}</strong></div>`; }
  });
  if(count===0){ html='<p style="text-align:center;color:#6b7280;padding:20px">No payments entered</p>'; document.getElementById('modalSubmitBtn').disabled=true; }
  else { html+=`<div style="margin-top:12px;padding:12px;background:#f0f7ff;border-radius:8px;display:flex;justify-content:space-between;font-weight:800"><span>Total (${count})</span><span>UGX ${total.toLocaleString()}</span></div>`; document.getElementById('modalSubmitBtn').disabled=false; }
  document.getElementById('modalHeader').style.display='flex';
  document.getElementById('modalActions').style.display='flex';
  document.getElementById('modalSubmitBtn').innerHTML=`Submit ${count} Payments`;
  document.getElementById('modalContent').innerHTML=html; 
  document.getElementById('modalOverlay').classList.add('show');
}
function closeModal(){document.getElementById('modalOverlay').classList.remove('show');}

async function submitPayments(){
  const payload=[]; 
  document.querySelectorAll('#repayTable tbody tr[data-loan-id]').forEach(tr=>{
    const book=tr.querySelector('.book-field')?.value.trim(); const amount=tr.querySelector('.amount-field')?.value.trim(); const loan_id=tr.dataset.loanId;
    if(book&&amount) payload.push({book_number:book, loan_id:loan_id, amount:amount});
  });
  if(payload.length===0) return;
  
  const btn = document.getElementById('modalSubmitBtn');
  const orig = btn.innerHTML;
  btn.innerHTML = `<span class="spinner"></span> Saving ${payload.length}...`;
  btn.disabled = true;

  try{
    const res=await fetch(BULK_URL, {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF,'X-Requested-With':'XMLHttpRequest'}, body:JSON.stringify({repayments:payload})});
    const data=await res.json();
    if(data.success){
      const listHtml = (data.breakdown||[]).map(b=>`<div style="display:flex;justify-content:space-between;font-size:13px;padding:6px 0;border-bottom:1px solid #f3f4f6"><span>${b.client} • Book #${b.book_number}</span><span style="font-weight:700">UGX ${parseInt(b.amount).toLocaleString()}</span></div>`).join('');
      document.getElementById('modalHeader').style.display='none';
      document.getElementById('modalActions').style.display='none';
      document.getElementById('modalContent').innerHTML = `
        <div style="text-align:center;padding:8px 0">
          <div style="font-size:48px">
      <div style="animation: pop .4s cubic-bezier(.34,1.56,.64,1)">
      
<svg width="64" height="64" viewBox="0 0 64 64" fill="none">
  <circle cx="32" cy="32" r="28" fill="#16a34a"/>
  <path d="M20 32L28.5 40.5L44 24.5" stroke="white" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
</div>
<style>@keyframes pop{0%{transform:scale(0.5)}100%{transform:scale(1)}}</style>
      
          </div>
          <h3 style="font-weight:800;font-size:18px;margin-top:8px">${data.saved} Payments Recorded</h3>
          <p style="color:#6b7280;font-size:13px;margin-top:4px">UGX ${data.total_formatted} total saved</p>
          <div style="text-align:left;margin-top:16px;background:#f9fafb;border-radius:10px;padding:12px;max-height:160px;overflow:auto">${listHtml||''}</div>
          <div style="display:flex;gap:10px;margin-top:20px">
            <button onclick="handleSuccessClose()" class="btn-clear" style="flex:1">Add More</button>
            <a href="/" style="flex:1;background:#1e4a8a;color:white;border:none;padding:14px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;display:flex;justify-content:center;align-items:center;text-decoration:none">View Receipts</a>
          </div>
        </div>`;

      showToast(data.message, 'success');
    } else {
      showToast('Error: ' + (data.error || data.errors?.join(', ') || 'Failed'), 'error');
      btn.innerHTML = orig; btn.disabled = false;
    }
  } catch(err){
    showToast('Network error - check connection', 'error');
    btn.innerHTML = orig; btn.disabled = false;
  }
}

function handleSuccessClose(){
  closeModal();
  document.querySelectorAll('#repayTable tbody tr[data-loan-id]').forEach(tr=>{
    const b=tr.querySelector('.book-field'); const a=tr.querySelector('.amount-field');
    if(b?.value.trim() && a?.value.trim()){
      tr.classList.add('row-saved');
      b.value=''; a.value=''; b.classList.remove('is-valid','is-invalid');
    }
  });
  updateCount();
}

function clearAll(){ 
  document.querySelectorAll('.book-field, .amount-field').forEach(i=>{i.value=''; i.disabled=false; i.classList.remove('is-invalid','is-valid');}); 
  document.querySelectorAll('.row-error').forEach(e=>e.style.display='none'); 
  document.querySelectorAll('#repayTable tbody tr').forEach(tr=>tr.classList.remove('row-saved'));
  updateCount(); 
}
updateCount();

{% if messages %}
  {% for message in messages %}
    showToast("{{ message|escapejs }}", "{{ message.tags|default:'success' }}");
  {% endfor %}
{% endif %}
