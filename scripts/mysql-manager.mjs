#!/usr/bin/env node
/**
 * MySQL Docker 管理（根目录执行）
 * 用法: node scripts/mysql-manager.mjs <up|down|reset|logs|wait|status|sync-env|generate-sql>
 */
import { execSync, spawnSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { copyFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const COMPOSE_FILE = join(ROOT, 'docker-compose.yml');

const cmd = process.argv[2] || 'help';

async function main() {

function run(command, opts = {}) {
  console.log(`\n> ${command}\n`);
  execSync(command, { cwd: ROOT, stdio: 'inherit', ...opts });
}

function compose(args) {
  run(`docker compose -f "${COMPOSE_FILE}" ${args}`);
}

function syncEnv() {
  const example = join(ROOT, '.env.example');
  const apiEnv = join(ROOT, 'MediaCrawler-Api', '.env');
  const rootEnv = join(ROOT, '.env');

  if (!existsSync(rootEnv) && existsSync(example)) {
    copyFileSync(example, rootEnv);
    console.log('已创建根目录 .env');
  }

  const mysqlBlock = `# MySQL（由根目录 pnpm db:sync-env 同步）
MYSQL_DB_PWD=123456
MYSQL_DB_USER=root
MYSQL_DB_HOST=127.0.0.1
MYSQL_DB_PORT=3306
MYSQL_DB_NAME=media_crawler
`;

  let apiContent = '';
  if (existsSync(apiEnv)) {
    apiContent = readFileSync(apiEnv, 'utf8');
    if (!apiContent.includes('MYSQL_DB_HOST')) {
      apiContent = mysqlBlock + '\n' + apiContent;
    }
  } else if (existsSync(join(ROOT, 'MediaCrawler-Api', '.env.example'))) {
    apiContent = readFileSync(join(ROOT, 'MediaCrawler-Api', '.env.example'), 'utf8');
  } else {
    apiContent = mysqlBlock;
  }

  writeFileSync(apiEnv, apiContent, 'utf8');
  console.log(`已同步 MediaCrawler-Api/.env`);
}

async function waitHealthy(maxSeconds = 120) {
  const start = Date.now();
  while (Date.now() - start < maxSeconds * 1000) {
    const r = spawnSync(
      'docker',
      ['inspect', '-f', '{{.State.Health.Status}}', 'mediacrawler-mysql'],
      { encoding: 'utf8' },
    );
    const status = (r.stdout || '').trim();
    if (status === 'healthy') {
      console.log('MySQL 已就绪 (healthy)');
      return true;
    }
    process.stdout.write('.');
    await sleep(2000);
  }
  console.error('\n等待 MySQL 健康检查超时');
  return false;
}

function generateSql() {
  run('uv run python scripts/generate_tables_sql.py', { cwd: join(ROOT, 'MediaCrawler-Api') });
}

const actions = {
  async up() {
    syncEnv();
    compose('up -d');
    if (await waitHealthy()) {
      console.log('\n连接: mysql -h127.0.0.1 -P3306 -uroot -p123456 media_crawler');
    }
  },
  down() {
    compose('down');
  },
  async reset() {
    compose('down -v');
    syncEnv();
    compose('up -d');
    await waitHealthy();
    console.log('\n已清空数据卷并重新执行 sql/ 初始化脚本');
  },
  logs() {
    compose('logs -f mysql');
  },
  async wait() {
    await waitHealthy();
  },
  status() {
    compose('ps');
    spawnSync('docker', ['inspect', '-f', '{{.State.Health.Status}}', 'mediacrawler-mysql'], {
      stdio: 'inherit',
    });
  },
  'sync-env': syncEnv,
  'generate-sql': generateSql,
  help() {
    console.log(`
MediaCrawler MySQL 管理 (Docker)

  pnpm db:up           启动 MySQL 并同步 .env
  pnpm db:down         停止容器
  pnpm db:reset        删除数据卷并重新初始化（会重跑 sql/）
  pnpm db:logs         查看日志
  pnpm db:wait         等待健康检查
  pnpm db:status       容器状态
  pnpm db:sync-env     同步 MediaCrawler-Api/.env
  pnpm db:generate-sql 从 ORM 重新生成 sql/01_tables.sql

账号: root / 123456  数据库: media_crawler
`);
  },
};

  if (actions[cmd]) {
    await actions[cmd]();
  } else {
    console.error(`未知命令: ${cmd}`);
    actions.help();
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
