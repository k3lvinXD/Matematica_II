const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../static/js/main.js'), 'utf8');
const context = {document: {addEventListener() {}}, console};
vm.createContext(context); vm.runInContext(source, context);
for (const [latex, expected] of [
  [String.raw`\sqrt{x+1}`, 'sqrt(x+1)'],
  [String.raw`\frac{1}{\frac{x}{y}}`, '((1)/(((x)/(y))))'],
  [String.raw`x^{2}+y^{2}`, 'x^(2)+y^(2)'],
  [String.raw`\sqrt{\frac{x^{2}+1}{y}}`, 'sqrt(((x^(2)+1)/(y)))'],
  [String.raw`\sin^{-1}(x)`, 'asin(x)'],
  [String.raw`\sin(x)\cdot\pi`, 'sin(x)*pi'],
]) assert.equal(context.latexToSympy(latex), expected);
for (const latex of [String.raw`\frac{x}`,String.raw`\unknown{x}`,'x}']) assert.throws(()=>context.latexToSympy(latex));
assert(!source.includes('innerHTML'), 'Las respuestas externas no deben insertarse como HTML');
console.log('10 comprobaciones del editor y presentación superadas.');
