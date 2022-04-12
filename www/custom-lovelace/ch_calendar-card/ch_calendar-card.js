class ChineseCalendarCard extends Polymer.Element {

  static get template() {
    return Polymer.html`
      <style>
        :root {
          --main-bg-color: linear-gradient(to bottom,#03a9f4,#68d0ff);
          --main-title-color: white;
          --ch-highlight-color: #03a9f4;
          --cell-title-color: #515151;
          --cell-date-color: #aaa;
        }
        .icon_container {
          width: 40px;
        }
        .icon {
          width: 25px;
          height: 25px;
          display: inline-block;
          vertical-align: middle;
          background-size: contain;
          background-position: center center;
          background-repeat: no-repeat;
          text-indent: -9999px;
          margin-left: 10px;
        }
        .icon_state {
          width: 20px;
          height: 20px;
          display: inline-block;
          vertical-align: middle;
          background-size: contain;
          background-position: center center;
          background-repeat: no-repeat;
          text-indent: -9999px;
          margin-left: 10px;
        }        
        .card {
          padding: 0 18px 18px 18px;
        }
        .header div {
          display: flex;
        }
        .title {
          margin-left: 16px;
          font-size: 16px;
        }
        .date_solar {
          font-size: 30px;
          text-align: right;
          margin-right: 20px;
          padding-top: 20px;
          color: var(--main-title-color);
        }
        .date_week {
          font-size: 18px;
          color: var(--main-title-color);
          text-align: right;
          margin-right: 20px;
        }
        .date_lunar {
          font-size: 14px;
          color: var(--main-title-color);
          text-align: right;
          margin-right: 20px;
          margin-top: -10px;
        }
        .latest_title {
          color: var(--main-title-color);
          font-size: 14px;
          text-align: center;
          padding-top: 35px;
        }
        .latest_holiday {
          color: var(--main-title-color);
          font-size: 18px;
          text-align: center;
        }
        .latest_days {
          color: var(--main-title-color);
          font-size: 45px;
          text-align: center;
          padding-top: 20px;
          padding-bottom: 16px;
        }
        .latest_date {
          color: var(--main-title-color);
          font-size: 14px;
          text-align: center;
          padding-bottom: 50px;
        }
        .cell_l {
          text-align: left;
        }
        .cell_name {
          font-size: 16px;
          color: var(--cell-title-color);
        }
        .cell_date {
          color: var(--cell-date-color);
          font-size: 14px;
        }
        .cell_day_h {
          text-align: right;
          font-size: 16px;
          color: var(--ch-highlight-color);
        }
        .cell_day_n {
          text-align: right;
          font-size: 16px;
          color: var(--cell-title-color);          
        }
        .table {
          width: 100%;
          padding-right: 20px;
          padding-top: 12px;
          padding-bottom: 6px;
        }
        .container {
          background: var(--main-bg-color);
        }
        .list_container {
          padding-bottom: 20px;
        }
      </style>
      <ha-card>
        <div class="container" on-click="_moreInfo">
          <div style="align-items: baseline;">
            <div class="title">[[title]]</div>
          </div>

          <div class="date_solar">
            [[attributes.solar]]
          </div>

          <div class="date_week">
            <p class="icon_state" style="background: none, url([[getStateIcon(calendarEntity.state)]]) no-repeat; background-size: contain;"></p>
            [[attributes.week]]
          </div>
          <!--
          <div class="date_week">
            [[calendarEntity.state]]，[[attributes.week]]
          </div>
          -->
          <div class="date_lunar">
            [[attributes.lunar]]
          </div>
          <div class="latest_title">距离</div>
          <div class="latest_holiday">[[latestReminder.name]]</div>
          <div class="latest_days">[[latestReminder.days]]</div>
          <div class="latest_date">[[latestReminder.date]]</div>
        </div>
        <div class=list_container>
          <template is="dom-repeat" items="{{reminderList}}">
            <table class="table" border="0">
              <td class="icon_container">
                <i class="icon" style="background: none, url([[getIcon(index)]]) no-repeat; background-size: contain;"></i>
              </td>
              <td>
                <table>
                  <tr>
                    <td class="cell_name">{{item.name}}</td>
                  </tr>
                  <tr>
                    <td class="cell_date">{{item.date}}</td>
                  </tr>
                </table>
              </td>
              <template is="dom-if" if="[[item.highlight]]">
                <td class="cell_day_h">
                {{item.days}}
                <template is="dom-if" if="[[item.unit]]">
                  天
                </template>
              </td>
              </template>
              <template is="dom-if" if="[[!item.highlight]]">
                <td class="cell_day_n">
                {{item.days}}
                <template is="dom-if" if="[[item.unit]]">
                  天
                </template>
              </td>
              </template>
            </table>
            <template is="dom-if" if="[[!item.hiddenLine]]">
              <div style="float:right;width:90%;border-top:1px solid #f5f5f5;height:0.5px;"></div>
            </template>
          </template>
        </div>

      </ha-card>
    `;
  }

  static get properties() {

    return {
      config: Object,
      calendarEntity: {
        type: Object,
        observer: 'dataChanged',
      },
      attributes: Object,
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('Please define "calendar" entity in the card config');
    }
    this.config = config;
   }

  constructor() {
    super();

  }

  set hass(hass) {
    this._hass = hass;
    // this.lang = this._hass.selectedLanguage || this._hass.language;
    this.calendarEntity = this.config.entity in hass.states ? hass.states[this.config.entity] : null;
    if (!this.calendarEntity) {
      return;
    }
    var list = [];
    var attributes = this.calendarEntity.attributes['data'];
    if (!attributes) {
      return;
    }
    this.attributes = attributes;
    // attributes['term'] = '春分';
    // attributes['festival'] = '春节';
    // attributes['anniversary'] = 'cc纪念日';
    
    // attributes['nearest_anniversary'] = 'aa生日';
    // attributes['nearest_anniversary_date'] = '20200627';
    // attributes['nearest_anniversary_days'] = 130;
    
    // attributes['nearest_holiday'] = '端午节';
    // attributes['nearest_holiday_date'] = '2020-11-11';
    // attributes['nearest_holiday_days'] = 10;

    // attributes['calculate_age_past'] = 'aa和bb纪念日';
    // attributes['calculate_age_past_date'] = '1900-01-01';
    // attributes['calculate_age_past_interval'] = '20001010101';
    // attributes['calculate_age_past_description'] = '2年2月2日2小时2分2秒';

    // attributes['calculate_age_future'] = 'aa和bb纪念日';
    // attributes['calculate_age_future_date'] = '2030-01-01';
    // attributes['calculate_age_future_interval'] = '20001010101';
    // attributes['calculate_age_future_description'] = '2年2月2日2小时2分2秒';


    if (attributes['term']) {
      list.push({'name':'节气','date':'今天','days':attributes['term']});
    }

    if (attributes['festival']) {
      list.push({'name':'节假日','date':'今天','days':attributes['festival']});
    }

    if (attributes['anniversary']) {
      list.push({'name':'纪念日','date':'今天','days':attributes['anniversary']});
    }


    if (attributes['tomorrow_state']) {
      list.push({'name':'状态','date':'明天','days':attributes['tomorrow_state']});
    }

    var holiday_days = 0,anniversary_days = 0;
    var beAdd;
    if (attributes['nearest_holiday']) {
      var obj = {'name':attributes['nearest_holiday'],'date':attributes['nearest_holiday_date'],'days':attributes['nearest_holiday_days'],'unit':'天','highlight':true};
        this.latestReminder = obj;
    }
    if (attributes['nearest_anniversary']) {
      var obj = {'name':attributes['nearest_anniversary'],'date':attributes['nearest_anniversary_date'],'days':attributes['nearest_anniversary_days'],'unit':'天','highlight':true};
        if (this.latestReminder) {
          if (this.latestReminder['days'] > obj['days']) {
            beAdd = this.latestReminder;
            this.latestReminder = obj;
          } else {
            beAdd = obj;
          }
        } else {
          this.latestReminder = obj;
        }

    }

    if (attributes.hasOwnProperty('next_anniversaries')) {
        var next_anniversaries = attributes['next_anniversaries'];
        for (var i = 0; i < next_anniversaries.length;i++) {
          var dict = next_anniversaries[i];
	      list.push({'name':dict['name'],'date':dict['date'],'days':dict['days'],'unit':'天','highlight':true});
        }    
    }


    if (beAdd) {
      list.push(beAdd);
    }

    if (attributes.hasOwnProperty('future_dates')) {
      var future_dates = attributes['future_dates'];
      for (var i = 0; i < future_dates.length;i++) {
        var dict = future_dates[i];
        list.push({'name':dict['name'],'date':dict['date'],'days':dict['description'],'highlight':true});
      }
    }


    if (attributes.hasOwnProperty('past_dates')) {
      var past_dates = attributes['past_dates'];
      for (var i = 0; i < past_dates.length;i++) {
        var dict = past_dates[i];
        list.push({'name':dict['name'],'date':dict['date'],'days':dict['description']});
      }      
    }

    var info = attributes['holiday_info']
    if (info) {
        list.push({'days':info});    
      }

    var last = list[list.length-1];
    last['hiddenLine'] = true;

    this.reminderList = list;

  }

  dataChanged() {
    // this.HourlyForecastChartData = this.drawChart('hourly', this.hourlyForecast);
    // this.DailyForecastChartData = this.drawChart('daily', this.dailyForecast);
  }


  getIcon(index) {
    return `${
      this.config.icons
    }${
      index
    }.png`;
  }

  getStateIcon(state) {
	var stateIcons = [{state:'工作日', icon:'working'},{state:'休息日', icon:'dating'},{state:'节假日', icon:'vacation'}];
	var iconName = "";
	
	stateIcons.forEach(function(item, index) {
        if(item.state == state) {
            iconName = item.icon;
            return true;
        }
    });		
	
    return `${
      this.config.icons
    }${
      iconName
    }.png`;
  }

  _fire(type, detail, options) {
    const node = this.shadowRoot;
    options = options || {};
    detail = (detail === null || detail === undefined) ? {} : detail;
    const e = new Event(type, {
      bubbles: options.bubbles === undefined ? true : options.bubbles,
      cancelable: Boolean(options.cancelable),
      composed: options.composed === undefined ? true : options.composed
    });
    e.detail = detail;
    node.dispatchEvent(e);
    return e;
  }

  _moreInfo() {
    this._fire('hass-more-info', { entityId: this.config.entity });
  }
}


customElements.define('ch_calendar-card', ChineseCalendarCard);
