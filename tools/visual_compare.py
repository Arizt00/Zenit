"""Compare real captures with the supplied golden masters; no fidelity percentage.

Reports geometry separately from colour/edge differences. Source and runtime
text can legitimately differ, so pixel MAE alone never certifies completion.
"""
import argparse,json
from pathlib import Path
from PIL import Image,ImageChops,ImageEnhance,ImageStat
ROOT=Path(__file__).resolve().parents[1]
def block_ssim(first,second):
    # Luma structure at quarter resolution. This is a diagnostic, not fidelity %.
    a=first.convert('L').resize((418,229),Image.Resampling.LANCZOS);b=second.convert('L').resize(a.size,Image.Resampling.LANCZOS);values=[]
    for y in range(0,a.height,16):
        for x in range(0,a.width,16):
            bounds=(x,y,min(x+16,a.width),min(y+16,a.height));p=list(a.crop(bounds).tobytes());q=list(b.crop(bounds).tobytes());n=len(p);u=sum(p)/n;v=sum(q)/n
            va=sum((z-u)**2 for z in p)/n;vb=sum((z-v)**2 for z in q)/n;cov=sum((i-u)*(j-v) for i,j in zip(p,q))/n
            values.append(((2*u*v+6.5025)*(2*cov+58.5225))/((u*u+v*v+6.5025)*(va+vb+58.5225)))
    return sum(values)/len(values)

def compare(reference,actual,out):
    ref=Image.open(reference).convert('RGB');image=Image.open(actual).convert('RGB')
    if ref.size==(1672,941) and image.size==(1672,917):ref=ref.crop((0,24,1672,941))
    if ref.size!=image.size:raise ValueError(f'Viewport mismatch: {ref.size} != {image.size}; do not stretch captures.')
    Image.blend(ref,image,.5).save(out.with_name(out.name+'-overlay.png'))
    diff=ImageChops.difference(ref,image);ImageEnhance.Contrast(diff).enhance(4).save(out.with_name(out.name+'-diff.png'))
    mean=ImageStat.Stat(diff).mean
    low=ImageChops.difference(ref.resize((209,115),Image.Resampling.LANCZOS),image.resize((209,115),Image.Resampling.LANCZOS))
    return {'channelMAE':mean,'meanMAE':sum(mean)/3,'lowFrequencyMAE':sum(ImageStat.Stat(low).mean)/3,'lumaBlockSSIM':block_ssim(ref,image),'overlay':out.name+'-overlay.png','diff':out.name+'-diff.png'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--captures',type=Path,required=True);p.add_argument('--references',type=Path,default=ROOT/'tests/visual/references');p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    result={}
    for name in ('editor','welcome','search','settings','forge','laboratory','debug','extensions'):
        actual=args.captures/(name+'.png');reference=args.references/(name+'.png')
        if actual.is_file() and reference.is_file():result[name]=compare(reference,actual,args.output/name)
    (args.output/'comparison.json').write_text(json.dumps({'screens':result,'interpretation':'Colour MAE and low-frequency MAE are diagnostics, not a fidelity score. Review overlays and geometry together.'},indent=2),encoding='utf-8')
    print(json.dumps({k:round(v['meanMAE'],2) for k,v in result.items()}))
if __name__=='__main__':main()
