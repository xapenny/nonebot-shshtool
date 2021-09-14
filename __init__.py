from nonebot.adapters.cqhttp.event import Event
from nonebot.plugin import on_command
from .data_source import get_payload
from nonebot.adapters.cqhttp import Bot
from nonebot.typing import T_State
import json
from pathlib import Path
from utils.utils import scheduler, get_bot

TXT_PATH = Path("PATH TO TXT")

__plugin_name__ = "备份SHSH"
__plugin_usage__ = "backup shsh "

shshtool = on_command("/SHSH", priority=5, block=True)


@shshtool.handle()
async def _(bot: Bot, event: Event, state: T_State):
    msg = str(event.get_message()).strip()
    if msg == '':
        await shshtool.finish("请输入正确的指令！\n或者发送 帮助 SHSH 获取帮助")
    elif msg == 'backup':
        await shshtool.send('请输入需要备份SHSH设备的ECID (14位 16进制)')
        state['operation'] = 'ecid'

@shshtool.receive()
async def _(bot: Bot, event: Event, state: T_State):
    msg = str(event.get_message()).strip()
    if msg == 'cancel':
        await shshtool.finish('已取消操作')
    elif state['operation'] == 'ecid':
        msg.upper()
        if len(msg) != 14:
            await shshtool.reject('ECID输入错误！\n请输入正确的ECID，或输入cancel取消')
        else:
            state['ecid'] = msg
            state['operation'] = 'find_pair'
            payload = await get_payload('apnonce_pair/', {'ecid': msg})
            payload_dict = json.loads(payload)
            if payload_dict['code'] == 0:
                state['apnonce'] = payload_dict['pair']['apnonce']
                state['generator'] = payload_dict['pair']['generator']
                apnonce = state['apnonce']
                generator = state['generator']
                state['operation'] = 'use_pair'
                await shshtool.reject(f'为您找到以下apnonce pair：\nGenerator: {generator}\nApNonce:{apnonce}\n\n要使用这对apnonce pair吗？\n回复use使用，dontuse手动输入，cancel取消操作')
    elif state['operation'] == 'use_pair':
        if msg == 'dontuse':
            state['operation'] = 'getgenerator'
            await shshtool.reject('请输入Generator(18位 以0x开头)')
        elif msg == 'use':
            state['operation'] = 'getdevicemodel'
            await shshtool.reject('请输入device model\n例如：iPhone12,1')
        else:
            await shshtool.reject('输入错误！请重新输入或输入cancel取消')
    elif state['operation'] == 'getgenerator':
        if len(msg) != 18:
            await shshtool.reject('输入有误！请重新输入或输入cancel取消')
        else:
            state['generator'] = msg
            state['operation'] = 'getapnonce'
            await shshtool.reject('请输入apnonce')
    elif state['operation'] == 'getapnonce':
        state['apnonce'] = msg
        state['operation'] = 'getdevicemodel'
        await shshtool.reject('请输入device model\n例如：iPhone12,1')
    elif state['operation'] == 'getdevicemodel':
        model_ok = 0
        model_list = ['iPhone','iPad','iPod']
        for i in model_list:
            if i in msg:
                model_ok += 1
        if model_ok:
            state['model'] = msg
            state['operation'] = 'getboardconfig'
            await shshtool.reject('请输入board config\n例如：N104AP')
    elif state['operation'] == 'getboardconfig':
        state['boardconfig'] = msg
        await shshtool.send('正在尝试保存SHSH……')
        try:
            payload = await get_payload('shsh3/', {'ecid': state['ecid'], 'boardconfig': state['boardconfig'], 'device': state['model'], 'selected_firmware': 'All', 'apnonce': state['apnonce'], 'generator': state['generator']})
        except:
            await shshtool.finish('出现未知错误！请稍后重试')
        payload_dict = json.loads(payload)
        if payload_dict['code'] == 0:
            return_str = '保存成功！\n'
            for key in payload_dict['builds']:
                return_str += '版本：{}({})\n设备型号：{}({})\nECID(尾号)：{}\nGenerator：0x{}\nApNonce：{}\n\n文件大小：{}\n下载地址：{}\n\n'.format(payload_dict['builds'][key]['version'], payload_dict['builds'][key]['build'], payload_dict['builds'][key]['device'], payload_dict['builds'][key]['boardconfig'], state['ecid'][-1:-5], payload_dict['builds'][key]['generator'], payload_dict['builds'][key]['nonce'], payload_dict['builds'][key]['size_str'], payload_dict['builds'][key]['url'])
            await shshtool.send(return_str)
            state['operation'] = 'setschedule'
            await shshtool.reject('是否为该设备设置定时备份？\n回复schedule确认 cancel取消')
        else:
            await shshtool.finish('保存失败！\n错误信息：{}'.format(payload_dict['message']))
    elif msg == 'schedule' and state['operation'] == 'setschedule':
        jsonData = readJson()
        writeJson(event.get_user_id(), True, state['ecid'], state['boardconfig'], state['model'], state['generator'], state['apnonce'], jsonData)
        await shshtool.finish('设置成功！备份每天执行一次。如果有新的版本将会私信通知您，请添加机器人为好友')
    else:
        await shshtool.reject('输入有误！请重新输入或输入cancel取消')
    
def readJson():
    with open(str(TXT_PATH) + '/shsh' + '/schedule.json', 'r') as f_in:
        data = json.load(f_in)
        f_in.close()
        return data


def writeJson(qq_id: str, enabled: bool, ecid: str, boardconfig: str, device: str, generator: str, apnonce: str, data: dict):
    with open(str(TXT_PATH) + '/shsh' + '/schedule.json', 'w') as f_out:
        data[qq_id] = {'enabled': enabled, 'ecid': ecid, 'boardconfig': boardconfig, 'device': device, 'generator': generator, 'apnonce': apnonce}
        json.dump(data, f_out)
        f_out.close()

@scheduler.scheduled_job(
    "cron",
    hour=6,
)
async def _scheduled_fetch_alert():
    jsonData = readJson()
    bot = get_bot()
    # bot.send_private_msg
    for qq in jsonData:
        return_str = 'SHSH保存成功！\n'
        try:
            if jsonData[qq]['enabled']:
                payload = await get_payload('shsh3/', {'ecid': jsonData[qq]['ecid'], 'boardconfig': jsonData[qq]['boardconfig'], 'device': jsonData[qq]['device'], 'selected_firmware': 'All', 'apnonce': jsonData[qq]['apnonce'], 'generator': jsonData[qq]['generator']})
                payload_dict = json.loads(payload)
                if payload_dict['code'] == 0:
                    try:
                        with open(str(TXT_PATH) + '/shsh' +'/mark','r', encoding='utf-8') as f:
                            f_data = f.read()
                            if f_data == list(payload_dict['builds'].keys())[-1]:
                                print('[SHSHTOOL] 没有新的版本，跳过……')
                                continue
                    except FileNotFoundError:
                        pass
                    for key in payload_dict['builds']:
                        return_str += '版本：{}({})\n设备型号：{}({})\nECID(尾号)：{}\nGenerator：0x{}\nApNonce：{}\n\n文件大小：{}\n下载地址：{}\n\n'.format(payload_dict['builds'][key]['version'], payload_dict['builds'][key]['build'], payload_dict['builds'][key]['device'], payload_dict['builds'][key]['boardconfig'], payload_dict['builds'][key]['ecid'][-1:-5], payload_dict['builds'][key]['generator'], payload_dict['builds'][key]['nonce'], payload_dict['builds'][key]['size_str'], payload_dict['builds'][key]['url'])
                    await bot.send_private_msg(user_id=qq, message=return_str)
                else:
                    await bot.send_private_msg(user_id=qq, message='尝试备份SHSH时出错！\n错误代码：{}\n：错误信息{}'.format(payload_dict['code'], payload_dict['message']))
            else:
                continue
        except KeyError:
            print('Tweak has been blocked by Nonebot Plugin Manager (NPM)!')
    with open(str(TXT_PATH) + '/shsh' +'/mark','w', encoding='utf-8') as f:
        f.write(list(payload_dict['builds'].keys())[-1])