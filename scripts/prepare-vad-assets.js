import {mkdirSync, copyFileSync, readdirSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..')
const destination=path.join(root,'frontend/public/vad')
mkdirSync(destination,{recursive:true})
for(const source of ['frontend/node_modules/@ricky0123/vad-web/dist','frontend/node_modules/onnxruntime-web/dist']) {
  const directory=path.join(root,source)
  for(const name of readdirSync(directory)) {
    if(name.endsWith('.onnx') || name==='vad.worklet.bundle.min.js' || /^ort-wasm.*\.(mjs|wasm)$/.test(name)) copyFileSync(path.join(directory,name),path.join(destination,name))
  }
}
console.log('VAD assets copied from installed dependencies.')
