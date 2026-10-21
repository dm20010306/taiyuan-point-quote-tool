export type Guide={axis:'x'|'y';value:number};
export type Bounds={left:number;right:number;top:number;bottom:number};
export type AlignmentIndex={x:number[][];y:number[][]};
const anchors=(b:Bounds)=>({x:[b.left,(b.left+b.right)/2,b.right],y:[b.top,(b.top+b.bottom)/2,b.bottom]});
export function alignmentIndex(boxes:Bounds[]):AlignmentIndex {
 const index:AlignmentIndex={x:[[],[],[]],y:[[],[],[]]};
 for(const box of boxes){const values=anchors(box);for(const axis of ['x','y'] as const)values[axis].forEach((v,i)=>index[axis][i].push(v))}
 for(const axis of ['x','y'] as const)index[axis].forEach(a=>a.sort((a,b)=>a-b));return index;
}
function nearest(sorted:number[],value:number){let lo=0,hi=sorted.length;while(lo<hi){const mid=(lo+hi)>>>1;if(sorted[mid]<value)lo=mid+1;else hi=mid}return [sorted[lo-1],sorted[lo]].filter(v=>v!==undefined).sort((a,b)=>Math.abs(a-value)-Math.abs(b-value))[0]}
export function snapMovement(boxes:Bounds[],index:AlignmentIndex,dx:number,dy:number,tolerance:number){
 const guides:Guide[]=[];let x=dx,y=dy;
 for(const axis of ['x','y'] as const){let best=tolerance+1,correction=0,target:number|undefined;
  for(const box of boxes)anchors(box)[axis].forEach((v,i)=>{const moved=v+(axis==='x'?dx:dy),match=nearest(index[axis][i],moved);if(match===undefined)return;const d=match-moved;if(Math.abs(d)<=tolerance&&Math.abs(d)<best){best=Math.abs(d);correction=d;target=match}});
  if(target!==undefined){if(axis==='x')x+=correction;else y+=correction;guides.push({axis,value:target})}
 }return {dx:x,dy:y,guides};
}
export function orthogonalEnd(start:{x:number;y:number},end:{x:number;y:number}){
 return Math.abs(end.x-start.x)>Math.abs(end.y-start.y)?{x:end.x,y:start.y}:{x:start.x,y:end.y};
}
