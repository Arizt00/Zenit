/** A repeated failure is evidence, never a successful verification. */
export function reproductionStatus(trial){
 const runs=trial.runs||[];
 if(runs.length!==2||runs.some(run=>!run.complete))return 'incomplete';
 if(!trial.stable)return 'different';
 if(runs.some(run=>run.code!==0||run.tests?.summary?.failed||run.tests?.summary?.error))return 'failed';
 return runs.every(run=>run.tests?.summary?.passed>0)?'passed':'repeated';
}
