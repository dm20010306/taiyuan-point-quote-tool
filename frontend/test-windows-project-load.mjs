import {chromium} from 'playwright';

const web=process.env.WINDOWS_LOAD_TEST_URL||'http://127.0.0.1:5187';
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900}});
const page=await context.newPage();
let projectCalls=0;

await context.route('**/api/**',async route=>{
  const url=new URL(route.request().url());const path=url.pathname.replace('/api','');
  if(path==='/projects'){
    projectCalls++;
    if(projectCalls===1)return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'NAS 同步服务暂不可用（模拟）'})});
    if(projectCalls===3)return route.fulfill({status:200,contentType:'application/json',body:'[]'});
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([{id:'cached-project',name:'缓存项目',customer:'测试客户',address:'测试地址',status:'进行中',signed:0,created_at:'2026-09-01',updated_at:'2026-09-30',point_count:3,total_price:'100.00'}])});
  }
  let body={};
  if(path==='/version')body={version:'2.0.1'};
  else if(path==='/brands'||path==='/products'||path==='/types')body=[];
  else if(path==='/knowledge-sync/status')body={brand_notes:0,project_notes:1,conflicts:[],sync_status:'waiting_sync',pending_count:0,failure_count:1,recent_error:'NAS 同步服务暂不可用'};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
});

try{
  await page.goto(web,{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:'项目读取失败'}).waitFor();
  await page.getByRole('main').getByText('NAS 同步服务暂不可用（模拟）').waitFor();
  if(await page.getByRole('heading',{name:'还没有项目'}).count())throw new Error('API failure must not be presented as an empty project library');
  await page.getByRole('button',{name:'重试读取'}).click();
  await page.getByText('缓存项目',{exact:true}).waitFor();
  if(projectCalls!==2)throw new Error(`expected one initial request and one retry, got ${projectCalls}`);
  const offlinePage=await context.newPage();
  await offlinePage.goto(web,{waitUntil:'networkidle'});
  await offlinePage.getByRole('heading',{name:'知识库尚未同步'}).waitFor();
  if(await offlinePage.getByRole('heading',{name:'还没有项目'}).count())throw new Error('an empty local cache while NAS is offline must not be reported as no projects');
  console.log('Windows startup project loading recovery passed: read errors are explicit and retry restores cached projects.');
}finally{
  await context.close();
  await browser.close();
}
