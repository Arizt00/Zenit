/** One output cursor per shared file; concurrent observers reuse the same read. */
export class SharedExecutions {
  constructor(request){this.request=request;this.records=new Map();}
  clear(){this.records.clear();}
  async read(path,run){
    if(!run||run.available===false)return null;
    let record=this.records.get(path);
    if(record?.job!==run.job){record={job:run.job,offset:0,text:'',done:false,code:null,pending:null};this.records.set(path,record);}
    if(record.done)return record;
    if(record.pending)return record.pending;
    record.pending=(async()=>{
      const data=await this.request({action:'job',job:record.job,offset:record.offset});
      record.text=(record.text+data.output).slice(-512000);record.offset=data.offset;record.done=data.done&&!data.more;record.code=data.code;
      record.interrupted=Boolean(data.interrupted);record.state=data.state;record.truncated=Boolean(data.truncated);
      return record;
    })();
    try{return await record.pending;}finally{record.pending=null;}
  }
}
