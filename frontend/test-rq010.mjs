import { chromium } from 'playwright';

const web = process.env.RQ010_WEB_URL || 'http://127.0.0.1:5180';
const api = process.env.RQ010_API_URL || 'http://127.0.0.1:8010/api';
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
  const projectName = `RQ-010 窗帘坐标测试 ${Date.now()}`;
  const project = await request('/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:projectName})});
  const upload = new FormData(); upload.append('file',new Blob([image],{type:'image/png'}),'窗帘坐标.png');
  await request(`/projects/${project.id}/drawings`,{method:'POST',body:upload});

  await page.goto(web,{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:projectName}).click();
  await page.locator('.drawing-stage').waitFor();
  await page.locator('.device-sidebar button').filter({hasText:'窗帘'}).click();

  const dragAt = async(start,end,label) => {
    const box = await page.locator('.drawing-stage').boundingBox();
    if (!box) throw new Error(`${label}: drawing stage missing`);
    const from={x:box.x+box.width*start[0],y:box.y+box.height*start[1]};
    const to={x:box.x+box.width*end[0],y:box.y+box.height*end[1]};
    await page.mouse.move(from.x,from.y); await page.mouse.down();
    await page.mouse.move(to.x,to.y,{steps:8}); await page.mouse.up();
    await page.waitForTimeout(120);
    const saved=await request(`/projects/${project.id}`);
    const curtains=saved.points.filter(point=>point.type_id==='curtain');
    const point=curtains.at(-1);
    const actual=[point.x,point.y,point.x2,point.y2], expected=[...start,...end];
    actual.forEach((value,index)=>{if(Math.abs(value-expected[index])>.008)throw new Error(`${label}: coordinate ${index} expected ${expected[index]}, got ${value}`)});
  };

  await dragAt([.18,.22],[.72,.64],'fit view');
  const viewport=await page.locator('.canvas-viewport').boundingBox();
  await page.mouse.move(viewport.x+viewport.width*.55,viewport.y+viewport.height*.5);
  await page.mouse.wheel(0,-650);
  await page.waitForTimeout(180);
  await dragAt([.24,.7],[.76,.3],'zoomed reverse vertical');

  const beforePan=await page.locator('.canvas-viewport').boundingBox();
  await page.mouse.move(beforePan.x+beforePan.width*.5,beforePan.y+beforePan.height*.5);
  await page.mouse.down({button:'middle'}); await page.mouse.move(beforePan.x+beforePan.width*.62,beforePan.y+beforePan.height*.58,{steps:6}); await page.mouse.up({button:'middle'});
  await page.waitForTimeout(120);
  await dragAt([.78,.72],[.3,.2],'panned reverse direction');

  await page.setViewportSize({width:1180,height:780});
  await page.evaluate(()=>{document.body.style.paddingTop='140px';window.scrollTo(0,120)});
  await page.waitForTimeout(180);
  await dragAt([.15,.8],[.65,.46],'resized and scrolled');
  console.log('RQ-010 passed: fit, zoom, pan, scroll, resize, consecutive and reverse curtain placement coordinates.');
} finally {
  await browser.close();
}
