# chinese holiday

### 日历及节假日显示组件

#############################################################################

2020.02.04 更新 - version:0.1.1

新增调用外部脚本机制：

目前是早上9点调用脚本，以后有需求可能会改成yaml配置

可以实现的功能：10.1国庆节还有14天的时候通知

配置文件（可以配置多个规则，但目前只有一个脚本）：
notify_script_name: 'test' //调用脚本名字
notify_principles: //调用脚本规则
  '14|7|1':  //未来某个日期（下面每个date字段对应）离现在还有 14 天 7天 1天时调用脚本
    - date: "1001" //需要调用脚本的日期
      solar: True

ios的通知脚本可以是：

注：下面的脚本中 message 是回调的拼接好的字符串，必须是这个字段名，
    message的内容大概为：距离xx生日还有xx天
test:
  sequence:
    - service: notify.mobile_app_xxx
      data_template:
        title: "节假日提醒"
        message: "{{ message }}"


#############################################################################


参考：https://bbs.hassbian.com/forum.php?mod=viewthread&tid=1237&highlight=农历

个人感觉有些地方不太适合我的场景的，所以重构了部分代码，增加了一些功能，去掉了一些功能。



![示例图](https://github.com/Crazysiri/chineseholiday/blob/master/snapshot.png)


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



配置文件：

```
sensor:
  - platform: chineseholiday
    name: holiday
    solar_anniversary:
      '0121':
        - aa生日
        - cc生日
      '0220':
        - bb生日
    lunar_anniversary:
      '0321':
        - aa农历生日
    calculate_age:
    	- date: '2022-10-10 10:23:10'
    	  name: 'aa和bb结婚两周年'
    notify_script_name: 'test'
    notify_principles:
      '14|7|1':
        - date: "0101"
          solar: True
```
