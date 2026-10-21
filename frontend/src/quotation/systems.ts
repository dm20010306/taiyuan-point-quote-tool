import type {SystemCategory} from './types';

export const SYSTEMS:SystemCategory[]=[
 {id:'central-control',order:1,name_zh:'中控系统',name_en:'Central Control System',icon:'monitor'},
 {id:'touch-control',order:2,name_zh:'触控系统',name_en:'Touch Control System',icon:'panel'},
 {id:'lighting-control',order:3,name_zh:'灯控系统',name_en:'Lighting Control System',icon:'light'},
 {id:'curtain',order:4,name_zh:'电动窗帘系统',name_en:'Motorized Curtain System',icon:'curtain'},
 {id:'hvac',order:5,name_zh:'暖通管理系统',name_en:'HVAC Management System',icon:'air'},
 {id:'music',order:6,name_zh:'背景音乐系统',name_en:'Music System',icon:'headphones'},
 {id:'network',order:7,name_zh:'网络系统',name_en:'Network System',icon:'wifi'},
 {id:'surveillance',order:8,name_zh:'监控系统',name_en:'Surveillance System',icon:'camera'},
 {id:'intercom',order:9,name_zh:'可视对讲系统',name_en:'Visual Intercom System',icon:'intercom'},
 {id:'equipment-cabinet',order:10,name_zh:'设备柜体',name_en:'Equipment Cabinet',icon:'cabinet'},
 {id:'cable',order:11,name_zh:'线材',name_en:'Cabling',icon:'cable'},
];
export const UNCATEGORIZED:SystemCategory={id:'uncategorized',order:99,name_zh:'未分类',name_en:'Uncategorized',icon:'other'};
