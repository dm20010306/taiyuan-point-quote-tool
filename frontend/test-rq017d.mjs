import {chromium} from 'playwright';

const web=process.env.RQ017D_WEB_URL||'http://127.0.0.1:5187';
const browser=await chromium.launch({headless:true});
const context=await browser.newContext();
const page=await context.newPage({viewport:{width:1440,height:900}});
let retryCount=0;
const waiting={brand_notes:14,project_notes:2,conflicts:[],sync_status:'waiting_sync',last_sync_at:'2026-09-30T10:30:00+08:00',pending_count:2,pending_items:[{entity_type:'project',entity_id:'a'.repeat(32)},{entity_type:'project',entity_id:'b'.repeat(32)}],failure_count:3,recent_error:'网络共享暂时不可用',error_type:'SMB_TIMEOUT',metrics:{brand_files_scanned:0,project_files_scanned:0,unchanged_entities_skipped:0,duration_ms:0}};
const synced={...waiting,sync_status:'synced',pending_count:0,pending_items:[],recent_error:'',error_type:''};

await page.route('**/api/**',async route=>{
  const url=new URL(route.request().url());
  const path=url.pathname.replace('/api','');
  let body={};
  if(path==='/version')body={version:'2.0.1'};
  else if(path==='/knowledge-sync/status')body=retryCount?synced:waiting;
  else if(path==='/knowledge-sync/retry'){retryCount++;body=synced}
  else if(path==='/projects'||path==='/brands'||path==='/products'||path==='/types')body=[];
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
});

try{
  await page.goto(web,{waitUntil:'networkidle'});
  const badge=page.getByRole('button',{name:'等待同步'});
  await badge.waitFor();
  await badge.click();
  const panel=page.getByRole('dialog',{name:'知识库同步'});
  await panel.getByText('网络共享暂时不可用').waitFor();
  await panel.getByText('3',{exact:true}).waitFor();
  await panel.getByRole('button',{name:'立即重试'}).click();
  await page.getByRole('button',{name:'已同步'}).waitFor();
  await panel.getByText('0 项').waitFor();
  await context.setOffline(true);
  await page.getByRole('button',{name:'等待同步'}).waitFor();
  if(!await panel.getByRole('button',{name:'立即重试'}).isDisabled())throw new Error('manual retry should be disabled while browser is offline');
  await context.setOffline(false);
  await page.getByRole('button',{name:'已同步'}).waitFor();
  console.log('RQ-017D passed: status details, pending count, manual retry recovery, and browser offline feedback.');
}finally{
  await context.close();
  await browser.close();
}
