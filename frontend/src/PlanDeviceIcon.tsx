import React from 'react';

type Props={type:string,size?:number,className?:string};

/** 与已确认的设备图标预览共用 48×48 图形；白底与阴影由外层容器绘制。 */
export default function PlanDeviceIcon({type,size=18,className='device-icon-svg'}:Props){
  const common={fill:'none',stroke:'currentColor',strokeWidth:3.3,strokeLinecap:'round' as const,strokeLinejoin:'round' as const};
  let symbol:React.ReactNode;
  switch(type){
    case 'switch': symbol=<><rect x="7" y="10" width="34" height="28" rx="5"/><path d="M24 11v26M13 17h5M30 17h5M13 31h5M30 31h5"/></>;break;
    case 'curtain': symbol=<><path d="M5 9h38"/><path d="M8 14h14v27H6c3-8 5-19 2-27Z" fill="currentColor" fillOpacity=".12"/><path d="M40 14H26v27h16c-3-8-5-19-2-27Z" fill="currentColor" fillOpacity=".12"/><path d="M14 15c3 8 2 18 0 25M34 15c-3 8-2 18 0 25"/></>;break;
    case 'sensor': symbol=<><path d="M24 12a12 12 0 0 1 12 12M24 12a12 12 0 0 0-12 12M24 18a6 6 0 0 1 6 6M24 18a6 6 0 0 0-6 6"/><circle cx="24" cy="28" r="4"/><path d="M18 39h12"/></>;break;
    case 'thermostat': symbol=<><path d="M20 9v22a8 8 0 1 0 8 0V9a4 4 0 0 0-8 0Z"/><path d="M24 16v19M33 14h7M33 21h5"/><circle cx="24" cy="36" r="3" fill="currentColor" stroke="none"/></>;break;
    case 'light': symbol=<><circle cx="24" cy="21" r="9"/><path d="M19 31h10M20 36h8M22 40h4M24 3v5M8 21h5M35 21h5M12 9l4 4M36 9l-4 4"/></>;break;
    case 'non_smart_area': symbol=<><path strokeDasharray="4 4" d="M7 8h34v32H7z"/><path d="M13 32l18-18M21 36l16-16"/></>;break;
    case 'lock': symbol=<><path d="M11 7h24v34H11zM17 19h11M17 24h8"/><circle cx="30" cy="31" r="2"/><path d="M35 24h7v14h-7"/></>;break;
    case 'camera': symbol=<><path d="M6 16h29l8 8-8 8H6zM13 32v6h19M23 38v5"/><circle cx="34" cy="24" r="4"/><path d="M9 21h17"/></>;break;
    case 'ceiling_ap': symbol=<><path d="M8 22a23 23 0 0 1 32 0M14 28a15 15 0 0 1 20 0M20 34a6 6 0 0 1 8 0"/><circle cx="24" cy="39" r="2.2" fill="currentColor" stroke="none"/></>;break;
    case 'wall_ap': symbol=<><path d="M8 17a23 23 0 0 1 32 0M14 24a14 14 0 0 1 20 0M20 31a6 6 0 0 1 8 0"/><circle cx="24" cy="37" r="2.2" fill="currentColor" stroke="none"/></>;break;
    case 'network': symbol=<><path d="M8 20a23 23 0 0 1 32 0M14 27a14 14 0 0 1 20 0M20 34a6 6 0 0 1 8 0"/><circle cx="24" cy="40" r="2.2" fill="currentColor" stroke="none"/></>;break;
    case 'water': symbol=<><path d="M24 5C17 17 12 23 12 30a12 12 0 0 0 24 0c0-7-5-13-12-25Z"/><path d="M19 31c1 3 3 5 7 5"/></>;break;
    case 'av': symbol=<><path d="M9 13h12l11-7v36l-11-7H9zM37 17c4 4 4 10 0 14M40 12c7 7 7 17 0 24"/></>;break;
    case 'system': symbol=<><rect x="13" y="13" width="22" height="22" rx="3"/><path d="M19 19h10v10H19zM18 5v8M30 5v8M18 35v8M30 35v8M5 18h8M5 30h8M35 18h8M35 30h8"/></>;break;
    default: symbol=<><path d="M24 5v9M24 34v9M5 24h9M34 24h9M11 11l6 6M31 31l6 6M37 11l-6 6M17 31l-6 6"/><circle cx="24" cy="24" r="7"/></>;break;
  }
  return <svg className={className} data-device-type={type} width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" {...common}>{symbol}</svg>;
}
