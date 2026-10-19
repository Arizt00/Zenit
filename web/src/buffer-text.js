// Monaco normalizes inserted newlines to the model's EOL. Comparing the wire
// representation literally would mistake that normalization for another edit.
export const sameBufferText=(a,b)=>a.replace(/\r\n?/g,'\n')===b.replace(/\r\n?/g,'\n');
