import {chromium} from 'playwright';

const web=process.env.RQ011_WEB_URL||'http://127.0.0.1:5181';
const api=process.env.RQ011_API_URL||'http://127.0.0.1:8011/api';
async function request(path,options={}){const response=await fetch(api+path,options);if(!response.ok)throw new Error(`${path}: ${response.status} ${await response.text()}`);return response.json()}

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1500,height:950}});
try{
  await page.setContent('<div style="width:1000px;height:650px;background:white"></div>');
  const image=await page.screenshot();
  const projectName=`RQ-011 快捷键测试 ${Date.now()}`;
  const project=await request('/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:projectName})});
  const upload=new FormData();upload.append('file',new Blob([image],{type:'image/png'}),'shortcut.png');
  await request(`/projects/${project.id}/drawings`,{method:'POST',body:upload});

  await page.goto(web,{waitUntil:'networkidle'});
  await page.evaluate(()=>localStorage.removeItem('pointquote.shortcuts.v1'));
  await page.reload({waitUntil:'networkidle'});
  await page.getByRole('heading',{name:projectName}).click();
  await page.locator('.drawing-stage').waitFor();

  await page.keyboard.press('w');
  if(!await page.locator('.device-sidebar button.active').filter({hasText:'窗帘'}).count())throw new Error('W did not select curtain');
  await page.keyboard.press('a');
  if(!await page.locator('.device-sidebar button.active').filter({hasText:'选择 / 框选'}).count())throw new Error('A did not select selection tool');

  const nameInput=page.locator('.drawing-name-field input');
  await nameInput.focus();await page.keyboard.press('e');
  if(await page.locator('.device-sidebar button.active').filter({hasText:'摄像头'}).count())throw new Error('letter shortcut fired while typing');
  await nameInput.evaluate(element=>element.blur());

  await page.keyboard.press('w');
  const before=await page.locator('.drawing-stage').boundingBox();
  const pointCount=(await request(`/projects/${project.id}`)).points.length;
  const viewport=await page.locator('.canvas-viewport').boundingBox();
  await page.keyboard.down('Space');await page.waitForTimeout(60);
  if(!await page.locator('.canvas-viewport.space-panning').count())throw new Error('Space temporary pan state missing');
  await page.mouse.move(viewport.x+viewport.width*.52,viewport.y+viewport.height*.52);await page.mouse.down();
  await page.mouse.move(viewport.x+viewport.width*.63,viewport.y+viewport.height*.61,{steps:6});await page.mouse.up();await page.keyboard.up('Space');
  await page.waitForTimeout(80);
  const after=await page.locator('.drawing-stage').boundingBox();
  if(Math.abs(after.x-before.x)<20||Math.abs(after.y-before.y)<20)throw new Error('Space drag did not pan canvas');
  if(!await page.locator('.device-sidebar button.active').filter({hasText:'窗帘'}).count())throw new Error('tool was not restored after Space');
  if((await request(`/projects/${project.id}`)).points.length!==pointCount)throw new Error('Space pan accidentally created a point');

  const stage=await page.locator('.drawing-stage').boundingBox();
  await page.mouse.move(stage.x+stage.width*.25,stage.y+stage.height*.3);await page.mouse.down();await page.mouse.move(stage.x+stage.width*.65,stage.y+stage.height*.6,{steps:5});await page.mouse.up();await page.waitForTimeout(100);
  if((await request(`/projects/${project.id}`)).points.length!==pointCount+1)throw new Error('test curtain was not created');
  await page.keyboard.press('Control+z');await page.waitForTimeout(100);
  if((await request(`/projects/${project.id}`)).points.length!==pointCount)throw new Error('default undo shortcut failed');
  await page.keyboard.press('Control+Shift+z');await page.waitForTimeout(100);
  if((await request(`/projects/${project.id}`)).points.length!==pointCount+1)throw new Error('default redo shortcut failed');
  await page.keyboard.press('Delete');await page.waitForTimeout(100);
  if((await request(`/projects/${project.id}`)).points.length!==pointCount)throw new Error('default delete shortcut failed');

  await page.getByRole('button',{name:'快捷键'}).click();
  const cameraKey=page.locator('[data-shortcut-action="camera"]');
  await cameraKey.focus();await page.keyboard.press('q');
  await page.getByRole('alert').filter({hasText:'已用于'}).waitFor();
  if(await cameraKey.textContent()!=='E')throw new Error('conflicting shortcut silently overwrote camera');
  await cameraKey.focus();await page.keyboard.press('u');
  await page.getByRole('button',{name:'保存设置'}).click();
  await page.keyboard.press('u');
  if(!await page.locator('.device-sidebar button.active').filter({hasText:'摄像头'}).count())throw new Error('custom shortcut did not activate camera');

  await page.reload({waitUntil:'networkidle'});
  await page.getByRole('heading',{name:projectName}).click();await page.locator('.drawing-stage').waitFor();
  await page.keyboard.press('u');
  if(!await page.locator('.device-sidebar button.active').filter({hasText:'摄像头'}).count())throw new Error('custom shortcut was not saved across reload');
  await page.getByRole('button',{name:'快捷键'}).click();await page.getByRole('button',{name:'恢复默认'}).click();await page.getByRole('button',{name:'保存设置'}).click();
  await page.keyboard.press('a');await page.keyboard.press('e');
  if(!await page.locator('.device-sidebar button.active').filter({hasText:'摄像头'}).count())throw new Error('restore defaults did not restore E for camera');
  console.log('RQ-011 passed: A selection, Space temporary pan/tool restore/no creation, input protection, conflict rejection, custom persistence and default restore.');
}finally{await browser.close()}
