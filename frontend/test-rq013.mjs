import {chromium} from 'playwright';

const web=process.env.RQ013_WEB_URL||'http://127.0.0.1:5183';
const api=process.env.RQ013_API_URL||'http://127.0.0.1:8013/api';
async function request(path,options={}){const response=await fetch(api+path,options);if(!response.ok)throw new Error(`${path}: ${response.status} ${await response.text()}`);return response}
async function json(path,options={}){return (await request(path,options)).json()}

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1500,height:950}});
try{
  await page.setContent('<div style="width:1000px;height:650px;background:white"></div>');
  const image=await page.screenshot();
  const projectName=`RQ-013 图例测试 ${Date.now()}`;
  const project=await json('/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:projectName})});
  const upload=new FormData();upload.append('file',new Blob([image],{type:'image/png'}),'legend.png');
  const drawing=await json(`/projects/${project.id}/drawings`,{method:'POST',body:upload});
  await page.goto(web,{waitUntil:'networkidle'});await page.getByRole('heading',{name:projectName}).click();await page.locator('.drawing-stage').waitFor();
  if(await page.locator('.drawing-legend').count())throw new Error('empty drawing should not show a legend');

  const stage=await page.locator('.drawing-stage').boundingBox();
  await page.keyboard.press('s');
  await page.mouse.click(stage.x+stage.width*.35,stage.y+stage.height*.42);await page.waitForTimeout(120);
  await page.mouse.click(stage.x+stage.width*.55,stage.y+stage.height*.52);await page.waitForTimeout(120);
  if(await page.locator('.legend-row[data-legend-type="sensor"]').count()!==1)throw new Error('same type was not deduplicated in legend');
  if(await page.locator('.legend-row').count()!==1)throw new Error('unexpected legend rows after duplicate sensor points');

  await page.keyboard.press('w');
  await page.mouse.move(stage.x+stage.width*.25,stage.y+stage.height*.72);await page.mouse.down();await page.mouse.move(stage.x+stage.width*.68,stage.y+stage.height*.72,{steps:6});await page.mouse.up();await page.waitForTimeout(150);
  if(await page.locator('.legend-row[data-legend-type="curtain"]').count()!==1||await page.locator('.legend-row').count()!==2)throw new Error('new type did not automatically join legend');

  const legend=page.locator('.drawing-legend');const before=await legend.boundingBox();
  await page.mouse.move(before.x+before.width/2,before.y+15);await page.mouse.down();await page.mouse.move(before.x+before.width/2+150,before.y+95,{steps:6});await page.mouse.up();await page.waitForTimeout(180);
  const saved=(await json(`/projects/${project.id}`)).drawings.find(item=>item.id===drawing.id);
  if(saved.legend_x<.12||saved.legend_y<.08)throw new Error(`legend position was not saved: ${saved.legend_x}, ${saved.legend_y}`);

  await page.reload({waitUntil:'networkidle'});await page.getByRole('heading',{name:projectName}).click();await page.locator('.drawing-stage').waitFor();
  const persisted=await page.locator('.drawing-legend').evaluate(element=>({left:element.style.left,top:element.style.top}));
  if(Math.abs(parseFloat(persisted.left)/100-saved.legend_x)>.002||Math.abs(parseFloat(persisted.top)/100-saved.legend_y)>.002)throw new Error('legend position did not survive reload');

  let current=await json(`/projects/${project.id}`);const curtain=current.points.find(point=>point.type_id==='curtain');
  await request(`/points/${curtain.id}`,{method:'DELETE'});
  await page.reload({waitUntil:'networkidle'});await page.getByRole('heading',{name:projectName}).click();await page.locator('.drawing-stage').waitFor();
  if(await page.locator('.legend-row[data-legend-type="curtain"]').count()||await page.locator('.legend-row').count()!==1)throw new Error('deleted last type stayed in legend');

  current=await json(`/projects/${project.id}`);
  for(const point of current.points)await request(`/points/${point.id}`,{method:'DELETE'});
  await page.reload({waitUntil:'networkidle'});await page.getByRole('heading',{name:projectName}).click();await page.locator('.drawing-stage').waitFor();
  if(await page.locator('.drawing-legend').count())throw new Error('legend remained after deleting all points');

  await json(`/projects/${project.id}/points?drawing_id=${drawing.id}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({type_id:'sensor',x:.4,y:.4})});
  const png=await request(`/projects/${project.id}/drawings/${drawing.id}/export.png?show_name=false&show_number=false`);
  const pdf=await request(`/projects/${project.id}/drawings/${drawing.id}/export.pdf?show_name=false&show_number=false`);
  if(!png.headers.get('content-type')?.includes('image/png')||(await png.arrayBuffer()).byteLength<10000)throw new Error('PNG export failed');
  const pdfBytes=new Uint8Array(await pdf.arrayBuffer());
  if(new TextDecoder().decode(pdfBytes.slice(0,4))!=='%PDF'||pdfBytes.byteLength<10000)throw new Error('PDF export failed');
  console.log('RQ-013 passed: automatic unique legend, add/remove updates, drag persistence, reload, PNG and PDF exports.');
}finally{await browser.close()}
