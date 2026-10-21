import { chromium } from 'playwright';

const web = process.env.RQ026_WEB_URL || 'http://127.0.0.1:5180';
const api = process.env.RQ026_API_URL || 'http://127.0.0.1:8010/api';
async function request(path, options={}) {
  const response = await fetch(api+path, options);
  if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
  return response.json();
}

const browser = await chromium.launch({headless:true});
const page = await browser.newPage({viewport:{width:1500,height:1000}});
try {
  await page.setContent('<div style="width:1000px;height:650px;background:white"></div>');
  const image = await page.screenshot();
  const projectName = `RQ-026 点位位置回归 ${Date.now()}`;
  const project = await request('/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:projectName})});
  const upload = new FormData(); upload.append('file',new Blob([image],{type:'image/png'}),'点位位置.png');
  await request(`/projects/${project.id}/drawings`,{method:'POST',body:upload});

  await page.goto(web,{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:projectName}).click();
  await page.locator('.drawing-stage').waitFor();
  await page.locator('.device-sidebar button').filter({hasText:'人体传感器'}).click();
  let stage=await page.locator('.drawing-stage').boundingBox();
  await page.mouse.click(stage.x+stage.width*.4,stage.y+stage.height*.35);
  await page.waitForTimeout(100);
  let saved=await request(`/projects/${project.id}`);
  let point=saved.points.find(item=>item.type_id==='sensor');
  if(!point||Math.abs(point.x-.4)>.01||Math.abs(point.y-.35)>.01)throw new Error(`click placement saved wrong coordinates: ${JSON.stringify(point)}`);
  let marker=page.locator(`[data-point="${point.id}"]`);
  let markerBox=await marker.boundingBox();
  if(Math.abs((markerBox.x+markerBox.width/2-stage.x)/stage.width-point.x)>.01||Math.abs((markerBox.y+markerBox.height/2-stage.y)/stage.height-point.y)>.01)throw new Error('marker rendered using pixel values instead of normalized drawing coordinates');

  await page.locator('.device-sidebar button').filter({hasText:'选择 / 框选'}).click();
  markerBox=await marker.boundingBox();
  await page.mouse.move(markerBox.x+markerBox.width/2,markerBox.y+markerBox.height/2);
  await page.mouse.down();
  await page.mouse.move(markerBox.x+markerBox.width/2+stage.width*.12,markerBox.y+markerBox.height/2-stage.height*.08,{steps:6});
  await page.mouse.up();
  await page.waitForTimeout(150);
  saved=await request(`/projects/${project.id}`);
  point=saved.points.find(item=>item.id===point.id);
  if(Math.abs(point.x-.52)>.015||Math.abs(point.y-.27)>.015)throw new Error(`drag did not persist expected normalized position: ${JSON.stringify(point)}`);
  marker=page.locator(`[data-point="${point.id}"]`);
  markerBox=await marker.boundingBox(); stage=await page.locator('.drawing-stage').boundingBox();
  if(Math.abs((markerBox.x+markerBox.width/2-stage.x)/stage.width-point.x)>.01||Math.abs((markerBox.y+markerBox.height/2-stage.y)/stage.height-point.y)>.01)throw new Error('dragged marker did not render at its saved position');
  console.log('RQ-026 passed: click placement renders at saved normalized coordinates and marker drag persists and renders its new position.');
} finally {
  await browser.close();
}
