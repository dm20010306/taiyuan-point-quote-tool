import {chromium} from 'playwright';

const web=process.env.QUOTE_SELECTION_WEB_URL||'http://127.0.0.1:5180';
const api=process.env.QUOTE_SELECTION_API_URL||'http://127.0.0.1:8000/api';
async function request(path,options={}){
  const response=await fetch(api+path,options);
  if(!response.ok)throw new Error(`${path}: ${response.status} ${await response.text()}`);
  return response.json();
}

const suffix=Date.now();
const productAName=`手选中控产品-A-${suffix}`;
const productBName=`手选触控产品-B-${suffix}`;
const json={headers:{'content-type':'application/json'}};
const browser=await chromium.launch({headless:true});
let project,productA,productB;
try{
  project=await request('/projects',{method:'POST',...json,body:JSON.stringify({name:`手动选品保留验证-${suffix}`})});
  productA=await request('/products',{method:'POST',...json,body:JSON.stringify({brand_name:'测试',name:productAName,system_category:'central-control',category:'智能',standard_price:'10.00'})});
  productB=await request('/products',{method:'POST',...json,body:JSON.stringify({brand_name:'测试',name:productBName,system_category:'touch-control',category:'智能',standard_price:'20.00'})});

  const page=await browser.newPage({viewport:{width:1500,height:1000}});
  await page.goto(web,{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:project.name}).click();
  await page.getByRole('button',{name:/进入报价/}).click();
  await page.getByRole('button',{name:'添加临时报价项目'}).click();
  const systems=page.locator('.quote-product-picker-tools label select');
  await systems.nth(0).selectOption('manual');
  await systems.nth(1).selectOption('central-control');
  const checkA=page.locator('.quote-product-select-list label').filter({hasText:productAName}).locator('input[type="checkbox"]');
  await checkA.check();
  await systems.nth(1).selectOption('touch-control');
  const checkB=page.locator('.quote-product-select-list label').filter({hasText:productBName}).locator('input[type="checkbox"]');
  await checkB.check();
  await systems.nth(1).selectOption('central-control');
  if(!await page.locator('.quote-product-select-list label').filter({hasText:productAName}).locator('input[type="checkbox"]').isChecked())throw new Error('切换系统后中控产品未保持勾选');
  await systems.nth(1).selectOption('touch-control');
  if(!await page.locator('.quote-product-select-list label').filter({hasText:productBName}).locator('input[type="checkbox"]').isChecked())throw new Error('切换系统后触控产品未保持勾选');
  if(await page.locator('.selected-count').innerText()!=='已选择 2 个产品')throw new Error('已选产品数量不正确');
  await page.getByRole('button',{name:'添加 2 个产品'}).click();
  await page.locator('.temporary-item-modal').waitFor({state:'detached',timeout:10000});
  const quote=await request(`/projects/${project.id}/quotation-v2`);
  const products=Object.fromEntries(quote.systems.map(system=>[system.category_id,system.items.map(item=>item.product_name)]));
  if(!products['central-control'].includes(productAName)||!products['touch-control'].includes(productBName))throw new Error(`产品系统归类错误：${JSON.stringify(products)}`);
  console.log('报价手动选品跨系统保留勾选：通过。');
}finally{
  if(project)await request(`/projects/${project.id}`,{method:'DELETE'}).catch(()=>{});
  if(productA)await request(`/products/${productA.id}`,{method:'DELETE'}).catch(()=>{});
  if(productB)await request(`/products/${productB.id}`,{method:'DELETE'}).catch(()=>{});
  await browser.close();
}
