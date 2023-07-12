# Chinese Holiday 中国节假日日历插件
## 日历及节假日显示组件
可以显示中国节假日, 周年, 纪念日, 生日等(支持农历和阴历)日历插件, 同时, 支持计算某个日期和时间已经过去了N年N月N天N小时N秒.

![示例图](https://github.com/Crazysiri/chineseholiday/blob/master/snaptshot_1.png)


# 安装
## HACS 安装(建议使用HACS安装和配置)
0. 手动添加自定义存储库 https://github.com/Crazysiri/chineseholiday 
1. HACS 添加集成 > 搜索 ```中国节假日日历```，点击下载

配合此集成的[前端卡片](https://github.com/Crazysiri/chineseholiday_card)

## 手动安装
下载 /custom_components/chineseholida 下的所有文件
复制到 \config\custom_components 
重启Home Assistant
此时应该可以在 配置 > 设备与服务 > 添加集成内搜索"chineseholiday" 或者 "中国节假日日历插件"

## 安装卡片，使用以下配置：

```
在页面添加下面的源
resources:
  - type: module
    url: /local/custom-lovelace/ch_calendar-card/ch_calendar-card.js

在添加卡片, 可以直接找到中国节假日日历的卡片, 或者 手动添加卡片, 填写下面的卡片配置代码

卡片配置
  - type: 'custom:ch_calendar-card'
    entity: sensor.holiday                                        
    icons: /local/custom-lovelace/ch_calendar-card/icons/

```

# 配置：
在configuration.yaml文件里,添加你的各种日期, 重启生效.

```
sensor:
  - platform: chineseholiday
    name: holiday
    solar_anniversary:
      '0121':
        - aa生日
        - cc生日
      '20200220': #这样配置会在显示的时候略有不一样，会以 bb生日(1岁) 的形式显示, 文案不包含 ‘生日’ 的统一显示为周年 xx纪念日（1周年）。
        - bb生日  #卡片前端aa生日(1岁)
        - aa和bb结婚纪念日 #卡片前端显示xx纪念日（1周年）
    lunar_anniversary:
      '0321':
        - aa农历生日
    calculate_age: #通过配置一个 'aa和bb结婚周年' '2022-10-10 10:23:10'(过去的时间)，1. 自动生成未来的时间将近的周年纪念日, 2.计算这个时间已经过去了N年N月N天N小时N秒
        - date: '2022-10-10 10:23:10'
          name: 'aa和bb结婚周年'
    notify_script_name: 'test' #调用脚本名字
    notify_times: #早上9点10分调用 13:00:00 下午1点调用
        - "09:10:00" 
        - "13:00:00"
    notify_principles: #调用脚本规则
      '14|7|1': #未来某个日期（下面每个date字段对应）离现在还有 14 天 7天 1天时调用脚本
        - date: "0101" #需要调用脚本的日期
          solar: False ##没填solar的默认为True 即阳历. false就是阴历, true是阳历 
        - date: "0102"  #需要调用脚本的日期 solar 不写 默认为True 即阳历
      '0': #0即为当天调用
        #*下面两种是特殊情况采用name，只有父亲节和母亲节 ，也就是填了name就不要填date，填name的只有这两种情况
        - name: "母亲节"
        - name: "父亲节"

```


# 更新


+ #### 2023.07.12 更新

版本 0.2.0

1.支持HACS

2.Polymer升级为Lit

#############################################################################

+ #### 2020.06.03 更新

1.修复当天的纪念日 不显示的问题

2.custom ui的 间距问题（应该是新版本导致的）

3.点击custom ui 可以进入控件的详情

4.控件详情的汉化

5.在最近的纪念日之后增加 接下来的纪念日，现在能同时显示更多自定义的纪念日了（目前支持两个，看后期需要增加yaml配置）

#############################################################################

+ #### 2020.03.30 更新 可以配置生日显示为：xx生日(10岁)

```
    #只对 下面文案中包含'生日'的有效 例如 - aa生日 在显示的时候变成 aa生日(1岁)
    # 文案不包含 ‘生日’ 的统一显示为周年 xx纪念日（1周年）。 
    solar_anniversary:
      '20200121': #该位置加入年即可
        - aa生日  #卡片前端aa生日(1岁)
        - xx纪念日 #卡片前端显示xx纪念日（1周年）
```

其它优化：根据论坛一个哥们的代码，将休息日，节假日，工作日改成icon（https://bbs.hassbian.com/forum.php?mod=viewthread&tid=9615&page=1#pid315704）


#############################################################################

+ #### 2020.02.19 更新 加入custom UI

```
ui-lovelace.yaml

resources:
  - type: module
    url: /local/custom-lovelace/ch_calendar-card/ch_calendar-card.js

卡片配置
  - type: 'custom:ch_calendar-card'
    entity: sensor.holiday                                        
    icons: /local/custom-lovelace/ch_calendar-card/icons/


```

#############################################################################

+ #### 2020.02.08 - version:0.1.3

新增功能：

1.外部调用脚本功能，支持母亲节和父亲节设置

详见最下面的脚本配置。

2.修复由于 utc 时间导致过一天不更新时间的bug

#############################################################################


+ #### 2020.02.06 - version:0.1.2

优化已有功能：

1.节气通过算法计算得出某年正确的值，取代现有写死的数据（节气每年都不一样，省得每年都改）

#############################################################################


+ #### 2020.02.19 更新 加入custom UI

```
ui-lovelace.yaml

resources:
  - type: module
    url: /local/custom-lovelace/ch_calendar-card/ch_calendar-card.js

卡片配置
  - type: 'custom:ch_calendar-card'
    entity: sensor.holiday                                        
    icons: /local/custom-lovelace/ch_calendar-card/icons/


```

#############################################################################

+ #### 2020.02.04 更新 - version:0.1.1

新增调用外部脚本机制：

目前是早上9点调用脚本，以后有需求可能会改成yaml配置

可以实现的功能：10.1国庆节还有14天的时候通知

配置文件（可以配置多个规则，但目前只有一个脚本）：

```
notify_script_name: 'test' //调用脚本名字
notify_times: //早上9点10分调用 13:00:00 下午1点调用
    - "09:10:00"
    - "13:00:00" 
notify_principles: //调用脚本规则
  '14|7|1':  //未来某个日期（下面每个date字段对应）离现在还有 14 天 7天 1天时调用脚本
    - date: "1001" //需要调用脚本的日期
      solar: False //非阳历 即阴历
    - date: "1002" //需要调用脚本的日期 solar 不写 默认为True 即阳历
```

ios的通知脚本可以是：

注：下面的脚本中 message 是回调的拼接好的字符串，必须是这个字段名，
    message的内容大概为：距离xx生日还有xx天

```
test:
  sequence:
    - service: notify.mobile_app_xxx
      data_template:
        title: "节假日提醒"
        message: "{{ message }}"
```


![示例图](https://github.com/Crazysiri/chineseholiday/blob/master/snapshot.png)

+ #### 参考
参考：
1. https://bbs.hassbian.com/thread-9133-1-1.html
2. https://bbs.hassbian.com/forum.php?mod=viewthread&tid=1237&highlight=农历

个人感觉有些地方不太适合我的场景的，所以重构了部分代码，增加了一些功能，去掉了一些功能。

+ #### 感谢：
1. WalterDSU提供Readme优化建议 https://github.com/WalterDSU



去掉的功能：

1.最近的纪念日

理由：

因为年份是固定的，所以每次（每年）还得修改

而且我也没找到使用场景



增加的功能：

1.每年的纪念日（包括阳历和阴历）

理由：

可纪念生日等每年都有的日子



优化的点：

1.全部纪念日可通过configuration.yaml配置文件配置而不用改代码

2.增加sqlite数据库 存取网络获取的节假日信息，因为发现L大的只获取当月的，会有有法定节日但是不显示的小问题，所以本插件采取数据库一次性获取6个月的数据，每天更新一次

3.其它：增加节气显示，增加星期显示等
