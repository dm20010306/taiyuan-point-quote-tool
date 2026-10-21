import {chromium} from 'playwright';

const web=process.env.RQ004_WEB_URL||'http://127.0.0.1:5187';
const browser=await chromium.launch({headless:true});
const context=await browser.newContext();
const page=await context.newPage({viewport:{width:1440,height:900}});
const reads=[];const writes=[];
const projects=[
  {id:'signed-project',name:'已签示例',customer:'客户甲',address:'地址一',status:'进行中',signed:1,created_at:'2026-09-01',updated_at:'2026-09-30',point_count:1,total_price:'100.00'},
  {id:'unsigned-project',name:'未签示例',customer:'客户乙',address:'地址二',status:'进行中',signed:0,created_at:'2026-09-01',updated_at:'2026-09-30',point_count:0,total_price:'0.00'},
];

await page.route('**/api/**',async route=>{
  const req=route.request();const url=new URL(req.url());const path=url.pathname.replace('/api','');
  if(req.method()==='PATCH')writes.push({path,body:req.postDataJSON()});
  if(req.method()==='GET'&&path==='/projects')reads.push(path);
  let body={};
  if(path==='/version')body={version:'2.0.1'};
  else if(path==='/projects')body=projects;
  else if(path==='/brands'||path==='/products'||path==='/types')body=[];
  else if(path.startsWith('/projects/')&&path.endsWith('/signed'))body={ok:true};
  else if(path==='/knowledge-sync/status')body={brand_notes:0,project_notes:2,conflicts:[],sync_status:'synced',pending_count:0,failure_count:0};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
});

try{
  await page.goto(web,{waitUntil:'networkidle'});
  await page.getByText('已签示例',{exact:true}).waitFor();
  await page.getByText('未签示例',{exact:true}).waitFor();
  const initialReads=reads.length;
  const signedCard=page.locator('.project-card').filter({hasText:'已签示例'});
  if(!await signedCard.evaluate(el=>el.classList.contains('signed')))throw new Error('signed card should have its visual distinction');
  await signedCard.getByRole('checkbox',{name:'已签'}).click();
  await signedCard.getByRole('checkbox',{name:'已签'}).waitFor({state:'visible'});
  await page.waitForFunction(()=>document.querySelector('.project-card .project-signed-toggle')?.getAttribute('aria-checked')==='false');
  if(await signedCard.evaluate(el=>el.classList.contains('signed')))throw new Error('unchecking should immediately remove signed-card distinction');
  if(writes.length!==1||writes[0].path!='/projects/signed-project/signed'||writes[0].body.signed!==false)throw new Error('toggle should issue exactly one signed-status PATCH');
  if(reads.length!==initialReads)throw new Error('toggle should not reload project list');
  await signedCard.getByRole('checkbox',{name:'已签'}).click();
  await page.waitForFunction(()=>document.querySelector('.project-card .project-signed-toggle')?.getAttribute('aria-checked')==='true');
  if(!await signedCard.evaluate(el=>el.classList.contains('signed')))throw new Error('checking should immediately restore signed-card distinction');
  if(writes.length!==2||writes[1].body.signed!==true||reads.length!==initialReads)throw new Error('rechecking should PATCH without reloading the list');
  await page.getByLabel('只查看已签项目').check();
  if(await page.getByText('未签示例',{exact:true}).count())throw new Error('signed-only filter should hide unsigned projects');
  await page.getByText('已签示例',{exact:true}).waitFor();
  await page.getByLabel('只查看已签项目').uncheck();
  await page.getByText('未签示例',{exact:true}).waitFor();
  console.log('RQ-004 signed workflow passed: immediate checkbox, signed-card distinction, PATCH without list refresh, and signed-only filtering.');
}finally{
  await context.close();
  await browser.close();
}
