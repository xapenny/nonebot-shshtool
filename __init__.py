from nonebot.adapters.cqhttp.event import Event
from nonebot.plugin import on_command
from .data_source import get_payload
from nonebot.adapters.cqhttp import Bot
from configs.path import TXT_PATH
from services.log import logger
from nonebot.typing import T_State
import json
from utils.utils import scheduler, get_bot

__plugin_name__ = "备份SHSH"
__plugin_usage__ = "backup shsh "

shshtool = on_command("/SHSH", priority=5, block=True)

@shshtool.handle()
async def _(bot: Bot, event: Event, state: T_State):
    msg = str(event.get_message()).strip()
    msg_list = msg.split()
    state['withdraw'] = True
    if msg == '':
        await shshtool.finish("请输入正确的指令！\n或者发送 帮助 SHSH 获取帮助")
    elif msg == 'backup':
        state['operation'] = 'getdevicemodel'
        await shshtool.send('请输入device model\n例如：iPhone12,1')
    elif msg == 'list':
        await shshtool.send('正在查询为您保存的设备')
        jsonData = readJson()
        count = 0
        return_str = '为您查询到以下信息\n'
        try:
            for entry in jsonData[str(event.get_user_id())]:
                count += 1
                ecid = entry["ecid"][0:6]
                for i in range(6, len(entry["ecid"])):
                    ecid += '*'
                return_str += f'{count}: {entry["nickname"]}\nECID: {ecid}\nGenerator: {entry["generator"]}\n已开启自动备份：{entry["enabled"]}\n\n'
            return_str += '如果要备份上述设备，请输入/SHSH backup 序号\n例如：/SHSH backup 1\n如果需要关闭自动备份，请输入/SHSH disable 序号'
        except:
            logger.info('[SHSHTOOL]没有查询到数据！')
            return_str = '没有查询到数据'
        await shshtool.finish(return_str)
    elif len(msg_list) == 2:
        jsonData = readJson()
        if msg_list[0] == 'backup':
            try:
                device_info = jsonData[str(event.get_user_id())][int(msg_list[1])-1]
                nickname = device_info['nickname']
                state['ecid'] = device_info['ecid']
                state['boardconfig'] = device_info['boardconfig']
                state['model'] = device_info['device']
                state['generator'] = device_info['generator']
                state['apnonce'] = device_info['apnonce']
                state['operation'] = 'getboardconfig'
                state['scheduled'] = True
                state['model_num'] = int(state['model'].replace('iPhone','').replace('iPad','').replace('iPod','').replace(',','')[0:-1])
                if ('iPhone' in state['model']) or ('iPad' in state['model']):
                    if state['model_num'] >= 11:
                        state['isA12'] = True
                    else:
                        state['isA12'] = False
                else:
                    state['isA12'] = False
            except Exception as ex:
                logger.info(f'[SHSHTOOL]遇到了错误：{ex}')
                await shshtool.finish('遇到了错误！请查看后台日志')
            await shshtool.send(f'准备备份 {nickname} 的SHSH\n回复ok开始，cancel取消')
        elif msg_list[0] == 'disable':
            try:
                jsonData[str(event.get_user_id())][int(msg_list[1])-1]['enabled'] = False
                with open(str(TXT_PATH) + '/shsh' + '/schedule.json', 'w') as f_out:
                    json.dump(jsonData, f_out)
                    f_out.close()
            except Exception as ex:
                logger.info(f'[SHSHTOOL]遇到了错误：{ex}')
                await shshtool.finish('遇到了错误！请查看后台日志')
            await shshtool.finish('操作成功完成')
        elif msg_list[0] == 'enable':
            try:
                jsonData[str(event.get_user_id())][int(msg_list[1])-1]['enabled'] = True
                with open(str(TXT_PATH) + '/shsh' + '/schedule.json', 'w') as f_out:
                    json.dump(jsonData, f_out)
                    f_out.close()
            except Exception as ex:
                logger.info(f'[SHSHTOOL]遇到了错误：{ex}')
                await shshtool.finish('遇到了错误！请查看后台日志')
            await shshtool.finish('操作成功完成')
        elif msg_list[0] == 'remove':
            try:
                del jsonData[str(event.get_user_id())][int(msg_list[1])-1]
                with open(str(TXT_PATH) + '/shsh' + '/schedule.json', 'w') as f_out:
                    json.dump(jsonData, f_out)
                    f_out.close()
            except Exception as ex:
                logger.info(f'[SHSHTOOL]遇到了错误：{ex}')
                await shshtool.finish('遇到了错误！请查看后台日志')
            await shshtool.finish('操作成功完成')


@shshtool.receive()
async def _(bot: Bot, event: Event, state: T_State):
    msg = str(event.get_message()).strip()
    try:
        await bot.delete_msg(message_id=event.message_id, self_id=int(bot.self_id))
    except Exception as ex:
        if state['withdraw']:
            await shshtool.send('尝试撤回您的消息失败！可能您是管理或我不是管理\n为保护隐私请自行撤回！')
        state['withdraw'] = False
        logger.info(f'[SHSHTOOL]撤回消息失败: {ex}')

    if msg == 'cancel':
        await shshtool.finish('已取消操作')

    elif state['operation'] == 'getdevicemodel':
        model_ok = 0
        model_list = ['iPhone','iPad','iPod']
        for i in model_list:
            if i in msg:
                model_ok += 1
        if model_ok:
            state['model'] = msg
            state['model_num'] = int(msg.replace('iPhone','').replace('iPad','').replace('iPod','').replace(',','')[0:-1])
            state['operation'] = 'ecid'
            await shshtool.reject('请输入需要备份SHSH设备的ECID (14位 16进制)')
        else:
            await shshtool.reject('输入有误！请重新输入或输入cancel取消')

    elif state['operation'] == 'ecid':
        # is A12?
        if ('iPhone' in state['model']) or ('iPad' in state['model']):
            if state['model_num'] >= 10:
                state['isA12'] = True
            else:
                state['isA12'] = False
        else:
            state['isA12'] = False

        msg.upper()
        if len(msg) != 14:
            await shshtool.reject('ECID输入错误！\n请输入正确的ECID，或输入cancel取消')
        else:
            state['scheduled'] = False
            state['ecid'] = msg
            if state['isA12']:
                state['operation'] = 'find_pair'
                await shshtool.send('该设备为A12+设备，正在向服务器查询Apnonce pair')
                payload = await get_payload('apnonce_pair/', {'ecid': msg})
                # logger.info(payload)
                payload_dict = json.loads(payload)
                if payload_dict['code'] == 0:
                    state['apnonce'] = payload_dict['pair']['apnonce']
                    state['generator'] = payload_dict['pair']['generator']
                    apnonce = state['apnonce']
                    generator = state['generator']
                    state['operation'] = 'use_pair'
                    await shshtool.reject(f'为您找到以下apnonce pair：\nGenerator: {generator}\nApNonce:{apnonce}\n\n要使用这对apnonce pair吗？\n回复use使用，dontuse手动输入，cancel取消操作')
                elif payload_dict['code'] == 405:
                    state['operation'] = 'use_pair'
                    await shshtool.reject('服务器上没有记录任何此设备信息\n发送 dontuse 来手动设置')
                else:
                    await shshtool.reject('发生未知错误：{}'.format(payload_dict['message']))
            else:
                state['operation'] = 'getgenerator'
                await shshtool.reject('检测到设备为A12以下芯片，跳过ApNonce设置\n请输入Generator(18位 以0x开头)')

    elif state['operation'] == 'use_pair':
        if msg == 'dontuse':
            state['operation'] = 'getgenerator'
            await shshtool.reject('请输入Generator(18位 以0x开头)')
        elif msg == 'use':
            # state['operation'] = 'getdevicemodel'
            # await shshtool.reject('请输入device model\n例如：iPhone12,1')
            state['operation'] = 'getboardconfig'
            await shshtool.reject('请输入board config\n例如：N104AP')
        else:
            await shshtool.reject('输入错误！请重新输入或输入cancel取消')

    elif state['operation'] == 'getgenerator':
        if len(msg) != 18:
            await shshtool.reject('输入有误！请重新输入或输入cancel取消')
        else:
            state['generator'] = msg
            if state['isA12']:
                state['operation'] = 'getapnonce'
                await shshtool.reject('请输入apnonce')
            else:
                state['operation'] = 'getboardconfig'
                await shshtool.reject('检测到设备为A12以下芯片，跳过ApNonce设置\n请输入board config\n例如：N104AP')

    elif state['operation'] == 'getapnonce':
        state['apnonce'] = msg
        state['operation'] = 'getboardconfig'
        await shshtool.reject('请输入board config\n例如：N104AP')

    elif state['operation'] == 'getboardconfig':
        if not state['scheduled']:
            state['boardconfig'] = msg
        state['operation'] = 'getsigned'
        await shshtool.send('正在查询开放验证的版本')
        signed_vers = await get_payload('shsh3/', {'device': state['model'], 'firmware': 'signed'})
        # logger.info(signed_vers)
        signed_dict = json.loads(signed_vers)
        if signed_dict['code'] == 0:
            ver_rt = ''
            state['version_ls'] = []
            state['legal_range'] = len(signed_dict['builds'])
            for ver in range(state['legal_range']):
                state['version_ls'].append('{} - {}'.format(signed_dict["builds"][list(signed_dict["builds"].keys())[ver]], list(signed_dict["builds"].keys())[ver]))
                logger.info(state['version_ls'][ver])
                ver_rt += f'[{ver}] iOS {signed_dict["builds"][list(signed_dict["builds"].keys())[ver]]}\n'
            ver_rt += '回复序号备份该版本，回复all备份所有版本'
            state['version_ls'].append('All')
            await shshtool.reject(ver_rt)
        else:
            await shshtool.finish(f'遇到了错误！\n\n错误代码: {signed_dict["code"]}\n错误信息: {signed_dict["message"]}')
        

    elif state['operation'] == 'getsigned':
        if msg.isnumeric():
            if (int(msg) <= state['legal_range']) and (int(msg) >= 0):
                state['version'] = state['version_ls'][int(msg)]
                state['operation'] = 'backup'
                await shshtool.reject('准备备份这台{}的SHSH\n回复ok开始，cancel取消'.format(state['model']))
            else:
                await shshtool.reject('输入错误！请重新输入')
        elif msg == 'all':
            state['version'] = state['version_ls'][-1]
            state['operation'] = 'backup'
            await shshtool.reject('准备备份这台{}的SHSH\n回复ok开始，cancel取消'.format(state['model']))
        else:
            await shshtool.reject('输入错误！请重新输入')

    elif (state['operation'] == 'backup') and (msg == 'ok'):
        await shshtool.send('正在尝试保存SHSH……')
        if state['isA12']:
            payload = await get_payload('shsh3/', {'ecid': state['ecid'], 'boardconfig': state['boardconfig'], 'device': state['model'], 'selected_firmware': state['version'], 'apnonce': state['apnonce'], 'generator': state['generator']})
        else:
            payload = await get_payload('shsh3/', {'ecid': state['ecid'], 'boardconfig': state['boardconfig'], 'device': state['model'], 'selected_firmware': state['version'], 'generator': state['generator']})
        if payload == -1:
            await shshtool.reject('连接超时！回复ok重试或回复cancel取消')
        # logger.info(payload)
        payload_dict = json.loads(payload)
        if payload_dict['code'] == 0:
            return_str = '保存成功！\n'
            ecid = state["ecid"][1:6]
            for i in range(6, len(state["ecid"])):
                ecid += '*'
            for key in payload_dict['builds']:
                try:
                    if state['isA12']:
                        return_str += '版本：{}({})\n设备型号：{}({})\nECID：{}\nGenerator：0x{}\nApNonce：{}\n\n文件大小：{}\n下载地址：{}\n\n'.format(payload_dict['builds'][key]['version'], payload_dict['builds'][key]['build'], payload_dict['builds'][key]['device'], payload_dict['builds'][key]['boardconfig'], ecid, payload_dict['builds'][key]['generator'], payload_dict['builds'][key]['nonce'], payload_dict['builds'][key]['size_str'], payload_dict['builds'][key]['url'])
                    else:
                        return_str += '版本：{}({})\n设备型号：{}({})\nECID：{}\nGenerator：0x{}\n\n文件大小：{}\n下载地址：{}\n\n'.format(payload_dict['builds'][key]['version'], payload_dict['builds'][key]['build'], payload_dict['builds'][key]['device'], payload_dict['builds'][key]['boardconfig'], ecid, payload_dict['builds'][key]['generator'], payload_dict['builds'][key]['size_str'], payload_dict['builds'][key]['url'])
                except KeyError:
                    return_str += '备份版本{}({})时出错！\n错误代码：{}\n错误信息：{}\n\n'.format(payload_dict['builds'][key]['params']['os'], payload_dict['builds'][key]['params']['build'], payload_dict['builds'][key]['code'], payload_dict['builds'][key]['message'])
            # logger.info(return_str)
            if state['scheduled']:
                await shshtool.finish(return_str)
            else:
                state['operation'] = 'setnickname'
                await shshtool.send(return_str)
                await shshtool.reject('是否为该设备设置定时备份？\n回复schedule确认 cancel取消')
        else:
            await shshtool.finish('保存失败！\n错误信息：{}'.format(payload_dict['message']))

    elif msg == 'schedule' and state['operation'] == 'setnickname':
        state['operation'] = 'setschedule'
        await shshtool.reject('请为该设备设置别名\n例如：Shiona\'s iPhone 11')

    elif state['operation'] == 'setschedule':
        nickname = msg
        jsonData = readJson()
        if not state['isA12']:
            state['apnonce'] = 'None'
        if writeJson(event.get_user_id(), True, nickname, state['ecid'], state['boardconfig'], state['model'], state['generator'], state['apnonce'], jsonData):
            await shshtool.finish('设置成功！备份每天执行一次。如果有新的版本将会私信通知您，请添加机器人为好友')
        else:
            await shshtool.finish('已经为该设备设置过定时备份，请不要重复设置！')

    else:
        await shshtool.reject('输入有误！请重新输入或输入cancel取消')
    
def readJson():
    with open(str(TXT_PATH) + '/shsh' + '/schedule.json', 'r') as f_in:
        data = json.load(f_in)
        f_in.close()
        return data

def writeJson(qq_id: str, enabled: bool, nickname: str, ecid: str, boardconfig: str, device: str, generator: str, apnonce: str, data: dict):
    try:
        for entry in data[qq_id]:
            if entry['ecid'] == ecid:
                return False
    except KeyError:
        logger.info('[SHSHTOOL]还没有保存过数据，继续……')
    with open(str(TXT_PATH) + '/shsh' + '/schedule.json', 'w') as f_out:
        try:
            print(data[qq_id])
        except KeyError:
            data[qq_id] = []
        data[qq_id].append({'enabled': enabled, 'nickname': nickname, 'ecid': ecid, 'boardconfig': boardconfig, 'device': device, 'generator': generator, 'apnonce': apnonce})
        json.dump(data, f_out)
        f_out.close()
    return True

@scheduler.scheduled_job(
    "cron",
    hour='*/23',
    # minute='*',
)
async def _scheduled_fetch_alert():
    jsonData = readJson()
    bot = get_bot()
    encounter_error = False
    global latest_ver
    for qq in jsonData:
        for k_device in jsonData[qq]:
            signed_vers = await get_payload('shsh3/', {'device': k_device['device'], 'firmware': 'signed'})
            signed_dict = json.loads(signed_vers)
            if signed_dict['code'] == 0:
                latest_ver = list(signed_dict["builds"].keys())[-1]
                latest_str = '{} - {}'.format(signed_dict["builds"][list(signed_dict["builds"].keys())[-1]], list(signed_dict["builds"].keys())[-1])
                logger.info(latest_str)
                try:
                    with open(str(TXT_PATH) + '/shsh' +'/mark','r', encoding='utf-8') as f:
                        f_data = f.read()
                        logger.info(f'[SHSHTOOL] 最新版本 {f_data} -> {latest_ver}')
                        if f_data == latest_ver:
                            logger.info('[SHSHTOOL] 没有新的版本，跳过……')
                            continue
                        else:
                            logger.info('[SHSHTOOL] 发现新的版本，准备开始备份')
                except FileNotFoundError:
                    pass
                return_str = 'SHSH保存成功！\n'
                try:
                    if k_device['enabled']:
                        payload = ''
                        cnt = 0
                        didFailed = True
                        while didFailed and cnt < 5:
                            cnt += 1
                            logger.info(f'[SHSHTOOL] 开始第{cnt}次尝试')
                            if k_device['apnonce'] == 'None':
                                payload = await get_payload('shsh3/', {'ecid': k_device['ecid'], 'boardconfig': k_device['boardconfig'], 'device': k_device['device'], 'selected_firmware': latest_str, 'generator': k_device['generator']})
                            else:    
                                payload = await get_payload('shsh3/', {'ecid': k_device['ecid'], 'boardconfig': k_device['boardconfig'], 'device': k_device['device'], 'selected_firmware': latest_str, 'apnonce': k_device['apnonce'], 'generator': k_device['generator']})
                            if 'Successfully' in payload:
                                didFailed = False
                            logger.info(payload)
                        if cnt > 5:
                            logger.error(f'[SHSHTOOL] 本次自动备份失败')
                            return
                        payload_dict = json.loads(payload)
                        if payload_dict['code'] == 0:
                            for key in payload_dict['builds']:
                                try:
                                    return_str += '版本：{}({})\n设备：{}\n\n文件大小：{}\n下载地址：{}\n\n'.format(payload_dict['builds'][key]['version'], payload_dict['builds'][key]['build'], k_device['nickname'], payload_dict['builds'][key]['size_str'], payload_dict['builds'][key]['url'])
                                except KeyError:
                                    encounter_error = True
                                    return_str += '备份版本{}({})时出错！\n错误代码：{}\n错误信息：{}\n\n'.format(payload_dict['builds'][key]['params']['os'], payload_dict['builds'][key]['params']['build'], payload_dict['builds'][key]['code'], payload_dict['builds'][key]['message'])
                            # logger.info(return_str)
                            if not encounter_error:
                                await bot.send_private_msg(user_id=qq, message=return_str)
                        else:
                            await bot.send_private_msg(user_id=qq, message='尝试备份SHSH时出错！\n错误代码：{}\n：错误信息{}'.format(payload_dict['code'], payload_dict['message']))
                    else:
                        continue
                except KeyError:
                    logger.error('Tweak has been blocked by Nonebot Plugin Manager (NPM)!')
            else:
                encounter_error = True
                continue
            
    if not encounter_error:
        logger.info('[SHSHTOOL] 正在写入标签……')
        with open(str(TXT_PATH) + '/shsh' +'/mark','w', encoding='utf-8') as f:
            f.write(latest_ver)
    else:
        logger.error('[SHSHTOOL] 备份过程中遇到错误！暂不写入标签')