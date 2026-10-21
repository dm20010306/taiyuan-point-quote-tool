import type {QuotationData,QuotationSystem} from './types';

export function calculateSystem(system:QuotationSystem){
 const subtotal=system.items.reduce((sum,item)=>sum+(item.visible?Math.max(0,item.quantity)*Math.max(0,item.unit_price_cents):0),0);
 const service=system.service_type==='percentage'?Math.round(subtotal*system.service_rate_basis/10000):system.service_type==='fixed'?Math.max(0,system.service_amount_cents):0;
 return {subtotal,service,total:subtotal+service};
}
export function calculateQuotation(data:QuotationData){
 const systems=data.systems.map(system=>({system,...calculateSystem(system)}));
 const base=systems.reduce((sum,row)=>sum+row.total,0);
 const discount=data.settings.discount_type==='percentage'?Math.round(base*data.settings.discount_value/10000):data.settings.discount_type==='fixed'?data.settings.discount_value:0;
 const safeDiscount=Math.min(base,Math.max(0,discount));
 const tax=Math.round((base-safeDiscount)*data.settings.tax_rate_basis/10000);
 const constructionFees=(data.construction_fees||[]).reduce((sum,fee)=>sum+Math.max(0,fee.amount_cents||0),0);
 return {systems,systemsTotal:base,discount:safeDiscount,tax,constructionFees,grandTotal:base-safeDiscount+tax+constructionFees};
}
export const currency=(cents:number,places=2)=>'¥'+(cents/100).toLocaleString('zh-CN',{minimumFractionDigits:places,maximumFractionDigits:places});
export const yuanToCents=(value:string|number)=>Math.round(Number(value||0)*100);
