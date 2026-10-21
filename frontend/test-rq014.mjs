import { chromium } from 'playwright';

const web=process.env.RQ014_WEB_URL||'http://127.0.0.1:5184';
const api=process.env.RQ014_API_URL||'http://127.0.0.1:8014/api';
async function request(path,options={}){const response=await fetch(api+path,options);if(!response.ok)throw new Error(`${path}: ${response.status} ${await response.text()}`);return response.json()}
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1450,height:950}});
try{
  await page.setContent('<div style="width:900px;height:600px;background:white"></div>');
  const image=await page.screenshot();
  const projectName=`RQ-014 Draft 测试 ${Date.now()}`;
  const project=await request('/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:projectName})});
  const upload=new FormData();upload.append('file',new Blob([image],{type:'image/png'}),'draft.png');
  await request(`/projects/${project.id}/drawings`,{method:'POST',body:upload});
  await page.goto(web,{waitUntil:'networkidle'});await page.getByRole('heading',{name:projectName}).click();await page.locator('.drawing-stage').waitFor();

  const cases=[
    {name:'窗帘',type:'curtain',preview:'.draft-svg'},
    {name:'摄像头',type:'camera',preview:'.draft-camera-range'},
    {name:'调光',type:'light',preview:'.draft-area:not(.draft-non-smart-area)'},
    {name:'非智能区域',type:'non_smart_area',preview:'.draft-non-smart-area'},
  ];
  for(const item of cases){
    await page.locator('.device-sidebar button').filter({hasText:item.name}).click();
    const box=await page.locator('.drawing-stage').boundingBox();
    const from={x:box.x+box.width*.22,y:box.y+box.height*.25},to={x:box.x+box.width*.68,y:box.y+box.height*.62};
    const before=(await request(`/projects/${project.id}`)).points.length;
    await page.mouse.move(from.x,from.y);await page.mouse.down();await page.mouse.move(to.x,to.y,{steps:7});
    if(await page.locator(item.preview).count()!==1)throw new Error(`${item.name}: drag preview missing`);
    const during=(await request(`/projects/${project.id}`)).points.length;
    if(during!==before)throw new Error(`${item.name}: draft was written before mouseup`);
    await page.mouse.up();await page.waitForTimeout(100);
    const saved=await request(`/projects/${project.id}`);
    if(saved.points.length!==before+1||saved.points.at(-1).type_id!==item.type)throw new Error(`${item.name}: mouseup did not commit exactly one object`);
  }

  await page.locator('.device-sidebar button').filter({hasText:'窗帘'}).click();
  const box=await page.locator('.drawing-stage').boundingBox();
  const before=(await request(`/projects/${project.id}`)).points.length;
  await page.mouse.move(box.x+box.width*.3,box.y+box.height*.3);await page.mouse.down();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.7,{steps:5});
  await page.keyboard.press('Escape');
  if(await page.locator('.draft-svg').count())throw new Error('Escape did not remove draft');
  await page.mouse.up();await page.waitForTimeout(100);
  if((await request(`/projects/${project.id}`)).points.length!==before)throw new Error('cancelled draft created a formal object');
  console.log('RQ-014 passed: four live previews, no pre-commit persistence, one commit on mouseup, Escape cancellation.');
}finally{await browser.close()}
