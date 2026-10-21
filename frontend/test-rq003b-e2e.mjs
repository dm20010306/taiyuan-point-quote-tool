import {chromium} from 'playwright';

const base=process.env.RQ003B_WEB_URL||'http://127.0.0.1:5175';
const api=process.env.RQ003B_API_URL||'http://127.0.0.1:8002/api';
async function request(path,options={}){
  const response=await fetch(api+path,options);
  if(!response.ok)throw new Error(`${path}: ${response.status} ${await response.text()}`);
  return response.json();
}
const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1500,height:1000}});
try{
  await page.setContent('<div style="width:800px;height:600px;background:white"></div>');
  const drawingPng=await page.screenshot();
  const projectName=`RQ-003B 区域布点端到端测试 ${Date.now()}`;
  const project=await request('/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:projectName})});
  const upload=new FormData();upload.append('file',new Blob([drawingPng],{type:'image/png'}),'区域测试.png');
  const drawing=await request(`/projects/${project.id}/drawings`,{method:'POST',body:upload});
  const createPoint=(body)=>request(`/projects/${project.id}/points?drawing_id=${drawing.id}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
  const light=await createPoint({type_id:'light',x:.12,y:.18,x2:.46,y2:.58});
  const nonSmart=await createPoint({type_id:'non_smart_area',x:.54,y:.18,x2:.88,y2:.58});

  await page.goto(base,{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:projectName}).click();
  await page.locator(`[data-point="${light.id}"]`).waitFor();
  const addInside=async(areaId,toolName,fx=.5,fy=.62)=>{
    await page.locator('.device-sidebar button').filter({hasText:toolName}).click();
    const box=await page.locator(`[data-point="${areaId}"]`).boundingBox();
    if(!box)throw new Error(`区域 ${areaId} 不可见`);
    await page.mouse.click(box.x+box.width*fx,box.y+box.height*fy);
    await page.waitForFunction(({areaId,toolName})=>{
      const selected=document.querySelector('.point-symbol.selected');
      return selected&&!selected.closest(`[data-point="${areaId}"]`)&&document.querySelector('.detail-sidebar')?.textContent?.includes(toolName);
    },{areaId,toolName});
  };

  await addInside(light.id,'人体传感器',.35,.62);
  await addInside(nonSmart.id,'温控器',.5,.62);
  await page.locator('.toolbar-group button').filter({has:page.locator('svg')}).nth(3).click();
  await addInside(light.id,'智能门禁',.72,.34);

  const saved=await request(`/projects/${project.id}`);
  for(const type of ['sensor','thermostat','lock']){
    if(!saved.points.some(point=>point.type_id===type))throw new Error(`${type} 未在区域内创建`);
  }

  await page.locator('.device-sidebar button').filter({hasText:'选择 / 框选'}).click();
  const lightBox=await page.locator(`[data-point="${light.id}"]`).boundingBox();
  await page.mouse.click(lightBox.x+8,lightBox.y+8);
  if(await page.locator(`[data-point="${light.id}"].selected`).count()!==1)throw new Error('选择工具无法选择区域空白');
  const sensor=saved.points.find(point=>point.type_id==='sensor');
  await page.locator(`[data-point="${sensor.id}"] .point-circle`).click();
  if(await page.locator(`[data-point="${sensor.id}"].selected`).count()!==1)throw new Error('区域内设备没有优先被选中');

  console.log('RQ-003B E2E passed: device placement inside light/non-smart areas, zoomed placement, area blank selection, device selection priority.');
} finally {
  await browser.close();
}
