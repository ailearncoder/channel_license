const apiBase = '/api'

function pretty(obj){
  try { return JSON.stringify(obj, null, 2) }
  catch(e){ return String(obj) }
}

function setBtnLoading(btn, loading){
  if(!btn) return
  if(loading){ btn.dataset.prev = btn.innerHTML; btn.innerHTML = '<span class="spinner"></span>' ; btn.disabled = true }
  else { btn.innerHTML = btn.dataset.prev || btn.innerHTML; btn.disabled = false }
}

async function apiFetch(path, opts){
  const res = await fetch(path, opts)
  if(res.headers.get('content-type')?.includes('application/json')){
    const body = await res.json()
    if(!res.ok) throw body
    return body
  }
  const text = await res.text()
  if(!res.ok) throw {error: text}
  return text
}

document.getElementById('btnLoadDevices').addEventListener('click', async (e) => {
  const btn = e.currentTarget
  setBtnLoading(btn, true)
  try{
    const includeExpired = document.getElementById('includeExpired').checked
    const data = await apiFetch(`${apiBase}/devices?include_expired=${includeExpired}`)
    document.getElementById('devicesResult').textContent = pretty(data)
  }catch(err){
    document.getElementById('devicesResult').textContent = pretty(err)
  }finally{ setBtnLoading(btn, false) }
})

document.getElementById('btnInitDb').addEventListener('click', async (e)=>{
  const btn = e.currentTarget
  setBtnLoading(btn, true)
  try{
    const data = await apiFetch(`${apiBase}/init_db`, { method:'POST' })
    alert('init db: ' + JSON.stringify(data))
  }catch(err){ alert('init failed: ' + JSON.stringify(err)) }
  finally{ setBtnLoading(btn, false) }
})

document.getElementById('btnAddChannel').addEventListener('click', async (e) => {
  const btn = e.currentTarget
  setBtnLoading(btn, true)
  try{
    const name = document.getElementById('ch_name').value.trim()
    if(!name){ document.getElementById('addChannelResult').textContent = '名称不能为空'; return }
    const max_devices = Number(document.getElementById('ch_max').value) || 1000
    const license_duration_days = Number(document.getElementById('ch_days').value) || 30
    const description = document.getElementById('ch_desc').value || null
    const payload = { name, max_devices, license_duration_days, description }
    const data = await apiFetch(`${apiBase}/channels`, {
      method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
    })
    document.getElementById('addChannelResult').textContent = pretty(data)
  }catch(err){ document.getElementById('addChannelResult').textContent = pretty(err) }
  finally{ setBtnLoading(btn, false) }
})

document.getElementById('btnDeleteChannel').addEventListener('click', async (e) => {
  const btn = e.currentTarget
  setBtnLoading(btn, true)
  try{
    const channel_id = document.getElementById('ch_id_del').value || null
    const channel_name = document.getElementById('ch_name_del').value || null
    const params = new URLSearchParams()
    if (channel_id) params.set('channel_id', channel_id)
    if (channel_name) params.set('channel_name', channel_name)
    const data = await apiFetch(`${apiBase}/channels?${params.toString()}`, { method: 'DELETE' })
    document.getElementById('deleteChannelResult').textContent = pretty(data)
  }catch(err){ document.getElementById('deleteChannelResult').textContent = pretty(err) }
  finally{ setBtnLoading(btn, false) }
})

document.getElementById('btnListChannels')?.addEventListener('click', async (e) => {
  const btn = e.currentTarget
  setBtnLoading(btn, true)
  try{
    const data = await apiFetch(`${apiBase}/channels`)
    document.getElementById('channelsResult').textContent = pretty(data)
  }catch(err){
    document.getElementById('channelsResult').textContent = pretty(err)
  }finally{ setBtnLoading(btn, false) }
})

document.getElementById('btnCopyDevices')?.addEventListener('click', async ()=>{
  const text = document.getElementById('devicesResult').textContent || ''
  try{ await navigator.clipboard.writeText(text); alert('已复制到剪贴板') }catch(e){ alert('复制失败') }
})

document.getElementById('btnClear')?.addEventListener('click', ()=>{
  document.getElementById('ch_id_del').value=''
  document.getElementById('ch_name_del').value=''
  document.getElementById('deleteChannelResult').textContent='未操作'
})
