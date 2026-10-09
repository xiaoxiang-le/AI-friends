/**
 * 构建后脚本：根据 Vite 打包生成的 index.html 中的资源路径，
 * 自动更新 Django 模板 backend/web/templates/index.html 里的 {% static %} 引用。
 * 用法（在项目根目录）：node scripts/update-django-static.js
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const builtIndexPath = path.join(ROOT, 'backend/static/frontend/index.html');
const djangoTemplatePath = path.join(ROOT, 'backend/web/templates/index.html');

const builtHtml = fs.readFileSync(builtIndexPath, 'utf8');

// 提取 script[src] 和 link[href] 的路径（如 /assets/index-XXX.js、/assets/index-XXX.css）
const scriptMatch = builtHtml.match(/<script[^>]*\ssrc="([^"]+)"[^>]*>/);
const linkMatch = builtHtml.match(/<link[^>]*\srel="stylesheet"[^>]*\shref="([^"]+)"[^>]*>/);

const scriptPath = scriptMatch ? scriptMatch[1].replace(/^\//, '') : null;  // assets/index-XXX.js
const cssPath = linkMatch ? linkMatch[1].replace(/^\//, '') : null;          // assets/index-XXX.css

if (!scriptPath || !cssPath) {
  console.error('update-django-static: 无法从打包结果中解析 script/link 路径');
  process.exit(1);
}

// 生成 Django static 路径：frontend/assets/xxx
const staticScript = `frontend/${scriptPath}`;
const staticCss = `frontend/${cssPath}`;

let template = fs.readFileSync(djangoTemplatePath, 'utf8');

// 只替换 {% static 'frontend/assets/...' %} 中的路径，保留标签结构
template = template.replace(
  /\{%\s*static\s+'frontend\/assets\/[^']+\.js'\s*%\}/,
  `{% static '${staticScript}' %}`
);
template = template.replace(
  /\{%\s*static\s+'frontend\/assets\/[^']+\.css'\s*%\}/,
  `{% static '${staticCss}' %}`
);

fs.writeFileSync(djangoTemplatePath, template);
console.log('update-django-static: 已更新', djangoTemplatePath);
console.log('  script:', staticScript);
console.log('  css:', staticCss);
