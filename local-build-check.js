#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🚀 开始本地构建验证...\n');

// 检查前端项目是否存在
const frontendPath = path.join(__dirname, 'vabhub-frontend');
if (!fs.existsSync(frontendPath)) {
  console.error('❌ 前端项目目录不存在');
  process.exit(1);
}

// 检查package.json是否存在
const packageJsonPath = path.join(frontendPath, 'package.json');
if (!fs.existsSync(packageJsonPath)) {
  console.error('❌ package.json 不存在');
  process.exit(1);
}

// 检查node_modules是否存在
const nodeModulesPath = path.join(frontendPath, 'node_modules');
if (!fs.existsSync(nodeModulesPath)) {
  console.log('📦 安装依赖包...');
  try {
    execSync('npm install', { cwd: frontendPath, stdio: 'inherit' });
    console.log('✅ 依赖安装完成');
  } catch (error) {
    console.error('❌ 依赖安装失败');
    process.exit(1);
  }
}

// 运行TypeScript类型检查
console.log('\n🔍 运行TypeScript类型检查...');
try {
  execSync('npm run typecheck', { cwd: frontendPath, stdio: 'inherit' });
  console.log('✅ TypeScript类型检查通过');
} catch (error) {
  console.error('❌ TypeScript类型检查失败');
  process.exit(1);
}

// 运行ESLint代码检查
console.log('\n📝 运行ESLint代码检查...');
try {
  execSync('npm run lint', { cwd: frontendPath, stdio: 'inherit' });
  console.log('✅ ESLint代码检查通过');
} catch (error) {
  console.error('❌ ESLint代码检查失败');
  process.exit(1);
}

// 运行构建测试
console.log('\n🏗️  运行构建测试...');
try {
  execSync('npm run build', { cwd: frontendPath, stdio: 'inherit' });
  console.log('✅ 构建测试通过');
} catch (error) {
  console.error('❌ 构建测试失败');
  process.exit(1);
}

console.log('\n🎉 所有检查通过！代码可以安全推送。');
console.log('💡 建议在推送前运行: git status 查看变更');
console.log('💡 推送命令: git push origin main');