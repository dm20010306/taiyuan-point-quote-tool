import {chromium} from 'playwright';

const web=process.env.RQ017B_WEB_URL||'http://127.0.0.1:5187';
const api=process.env.RQ017B_API_URL||'http://127.0.0.1:8017/api';
async function request(path,options={}){const response=await fetch(api+path,options);if(!response.ok)throw new Error(`${path}: ${response.status} ${await response.text()}`);return response.json()}

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1500,height:950}});
let project;
try{
  await page.setContent('<div style="width:900px;height:600px;background:white"></div>');
  const image=await page.screenshot();
  project=await request('/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:`RQ-017B 保存测试 ${Date.now()}`})});
  const upload=new FormData();upload.append('file',new Blob([image],{type:'image/png'}),'save.png');
  const drawing=await request(`/projects/${project.id}/drawings`,{method:'POST',body:upload});
  const point=await request(`/projects/${project.id}/points?drawing_id=${drawing.id}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({type_id:'sensor',x:.4,y:.4})});

  const writes=[];page.on('request',req=>{if(req.method()!=='GET')writes.push({method:req.method(),url:req.url()})});
  await page.goto(web,{waitUntil:'networkidle'});await page.getByRole('heading',{name:project.name}).click();await page.locator('.drawing-stage').waitFor();
  await page.locator(`.point-marker[data-point="${point.id}"]`).click();
  const quantity=page.locator('.detail-sidebar label').filter({hasText:'数量'}).locator('input');
  const beforePointWrites=writes.length;
  await quantity.fill('2');await quantity.fill('3');await quantity.fill('4');
  await page.waitForTimeout(350);
  if(writes.length!==beforePointWrites)throw new Error('point change was written before the 800ms debounce');
  await page.waitForTimeout(1150);
  const pointWrites=writes.slice(beforePointWrites).filter(item=>item.method==='PATCH'&&item.url.includes(`/api/points/${point.id}`));
  if(pointWrites.length!==1)throw new Error(`rapid point changes produced ${pointWrites.length} PATCH requests`);
  const saved=(await request(`/projects/${project.id}`)).points.find(item=>item.id===point.id);
  if(saved.quantity!==4)throw new Error(`debounced point value was not saved: ${saved.quantity}`);

  await page.getByRole('button',{name:/进入报价/}).click();await page.locator('.quotation-workspace').waitFor();
  const beforeSettings=writes.length;
  await page.getByRole('button',{name:'报价设置'}).click();await page.waitForTimeout(1100);
  const automaticSystemWrites=writes.slice(beforeSettings).filter(item=>item.method==='PATCH'&&item.url.includes('/api/quotation-systems/'));
  if(automaticSystemWrites.length)throw new Error(`opening settings produced ${automaticSystemWrites.length} unchanged system writes`);
  await page.getByRole('button',{name:'完成'}).click();

  const title=page.locator('.project-title-input');const beforeQuoteWrites=writes.length;
  await title.fill('防抖报价');await title.fill('防抖报价 A');await title.fill('防抖报价 AB');
  await page.getByRole('button',{name:'保存',exact:true}).click();await page.waitForTimeout(1200);
  const quoteWrites=writes.slice(beforeQuoteWrites).filter(item=>item.method==='PATCH'&&item.url.includes(`/api/projects/${project.id}/quotation-v2`));
  if(quoteWrites.length!==1)throw new Error(`merged quote save produced ${quoteWrites.length} PATCH requests`);
  console.log('RQ-017B passed: point debounce, merged manual quote save, and no settings-on-open writes.');
}finally{
  if(project)try{await request(`/projects/${project.id}`,{method:'DELETE'})}catch{}
  await browser.close();
}
