# chinese holiday

### 日历及节假日显示组件

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
      - "0121#aa生日#"
      - "0220#bb生日#"
    lunar_anniversary:
      - "0321#aa农历生日#"
    calculate_age:
    	- date: '2022-10-10 10:23:10'
    	  name: 'aa和bb结婚两周年'
```
