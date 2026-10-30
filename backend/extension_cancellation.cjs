'use strict';
const none=Object.freeze({isCancellationRequested:false,onCancellationRequested:()=>({dispose(){}})});
function source(){
 const listeners=new Set();let cancelled=false,disposed=false;
 const token={get isCancellationRequested(){return cancelled;},onCancellationRequested(fn){
  if(disposed)return {dispose(){}};
  if(cancelled){const job=setTimeout(()=>fn(),0);return {dispose:()=>clearTimeout(job)};}
  listeners.add(fn);return {dispose:()=>listeners.delete(fn)};
 }};
 return {token,cancel(){if(cancelled||disposed)return;cancelled=true;for(const fn of [...listeners])try{fn();}catch(error){console.error(error);}listeners.clear();},dispose(){disposed=true;listeners.clear();}};
}
module.exports={none,source};
