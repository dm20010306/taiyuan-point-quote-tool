import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const defaultRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../frontend/node_modules/playwright');
const playwrightRoot=process.env.POINT_QUOTE_PLAYWRIGHT_ROOT||defaultRoot;
const {chromium}=await import(pathToFileURL(path.join(playwrightRoot,'index.mjs')).href);

const [url, output] = process.argv.slice(2);
if (!url || !output) throw new Error('usage: render_quotation_pdf.mjs <url> <output>');
const browser = await chromium.launch({headless:true});
try {
  const page = await browser.newPage({viewport:{width:1600,height:900},deviceScaleFactor:1});
  await page.goto(url,{waitUntil:'networkidle',timeout:120000});
  await page.waitForFunction(()=>document.documentElement.dataset.quotationReady==='true',{timeout:120000});
  await page.evaluate(async()=>{
    await document.fonts.ready;
    await Promise.all(Array.from(document.images).map(image=>image.complete?Promise.resolve():new Promise(resolve=>{image.addEventListener('load',resolve,{once:true});image.addEventListener('error',resolve,{once:true})})));
  });
  await page.emulateMedia({media:'print'});
  await page.pdf({path:output,width:'320mm',height:'180mm',printBackground:true,preferCSSPageSize:true,displayHeaderFooter:false,margin:{top:'0',right:'0',bottom:'0',left:'0'}});
} finally {
  await browser.close();
}
