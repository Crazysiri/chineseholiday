class ChineseCalendarCard extends Polymer.Element {
  
  static get template() {
    return Polymer.html`
      <style>
        ha-icon {
          color: var(--paper-item-icon-color);
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
          color: var(--secondary-text-color);
        }
        .date_solar {
          font-size: 30px;
          color: var(--secondary-text-color);
          text-align: right;
          margin-right: 20px;
        }
        .date_week {
          font-size: 18px;
          color: var(--secondary-text-color);
          text-align: right;
          margin-right: 20px;
        }
        .date_lunar {
          font-size: 14px;
          color: var(--secondary-text-color);
          text-align: right;
          margin-right: 20px;          
        }     
        .latest_title {
          font-size: 14px;
          text-align: center;          
        }
        .latest_holiday {
          font-size: 16px;
          text-align: center;                    
        }  
        .latest_days {
          font-size: 30px;
          text-align: center;                    
        } 
        .latest_date {
          font-size: 14px;
          text-align: center;                    
        }
        .cell_r {
          text-align: right;          
        } 
        .cell_l {
          text-align: left;          
        }             
        .table {
          width: 100%;          
        }                        
      </style>
      <ha-card>
        <div style="align-items: baseline;">
          <div class="title">[[title]]</div>
        </div>
        
        <div class="date_solar">
          [[calendarEntity.attributes.solar]]
        </div>
        <div class="date_week">
          [[calendarEntity.attributes.week]]
        </div>
        <div class="date_lunar">
          [[calendarEntity.attributes.lunar]]
        </div>
        <div class="latest_title">距离</div>
        <div class="latest_holiday">[[latestReminder.name]]</div>
        <div class="latest_days">[[latestReminder.days]]</div>
        <div class="latest_date">[[latestReminder.date]]</div> 
        <template is="dom-repeat" items="{{reminderList}}">
          <table class="table" border="0">
            <td width="20px"><ha-icon icon="mdi:update"></ha-icon></td>
            <td>
              <table>
                <tr>
                  <td>{{item.name}}</td>
                </tr>
                <tr>
                  <td>{{item.date}}</td>
                </tr>
              </table>
            </td>
            <td class="cell_r">{{item.days}}</td>                        
          </table>
        </template>

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
    var list = [];
    var attributes = this.calendarEntity.attributes; 
    
    // attributes['term'] = '春分';
    // attributes['festival'] = '春节';
    // attributes['anniversary'] = 'cc纪念日';
    
    // attributes['nearest_anniversary'] = 'aa生日';
    // attributes['nearest_anniversary_date'] = '2020-11-10';
    // attributes['nearest_anniversary_days'] = '9';

    // attributes['nearest_holiday'] = '端午节';
    // attributes['nearest_holiday_date'] = '2020-11-11';
    // attributes['nearest_holiday_days'] = '10';
    
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

    var holiday_days = 0,anniversary_days = 0;
    var beAdd;
    if (attributes['nearest_holiday']) {
      var obj = {'name':attributes['nearest_holiday'],'date':attributes['nearest_holiday_date'],'days':attributes['nearest_holiday_days']};
        this.latestReminder = obj;
    }
    if (attributes['nearest_anniversary']) {
      var obj = {'name':attributes['nearest_anniversary'],'date':attributes['nearest_anniversary_date'],'days':attributes['nearest_anniversary_days']};
        if (this.latestReminder && Number(this.latestReminder['days']) > Number(obj['days'])) {
          beAdd = this.latestReminder;
          this.latestReminder = obj;          
        }

    }

    if (beAdd) {
      list.push(beAdd);
    }

    if (attributes['calculate_age_past']) {
        list.push({'name':attributes['calculate_age_past'],'date':attributes['calculate_age_past_date'],'days':attributes['calculate_age_past_description']});
    }    
    if (attributes['calculate_age_future']) {
        list.push({'name':attributes['calculate_age_future'],'date':attributes['calculate_age_future_date'],'days':attributes['calculate_age_future_description']});
    }            
    this.reminderList = list;

  }

  dataChanged() {
    // this.HourlyForecastChartData = this.drawChart('hourly', this.hourlyForecast);
    // this.DailyForecastChartData = this.drawChart('daily', this.dailyForecast);
  }


  getWeatherIcon(condition) {
    return `${
      this.config.icons
        ? this.config.icons
        : "https://cdn.jsdelivr.net/gh/bramkragten/custom-ui@master/weather-card/icons/animated/"
    }${
      this.sunObj.state && this.sunObj.state == "below_horizon"
        ? this.weatherIconsNight[condition]
        : this.weatherIconsDay[condition]
    }.svg`;
  }

}


customElements.define('ch_calendar-card', ChineseCalendarCard);



