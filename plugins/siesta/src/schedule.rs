// Copyright (c) 2026 Luis Liñán
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

//! The weekly draw time: which scheduled draw is the latest one due.

use chrono::{DateTime, Datelike, Days, NaiveDate, TimeZone};
use chrono_tz::Tz;

use crate::config::Schedule;

/// The latest scheduled draw at or before `now`.
pub fn latest_slot(schedule: &Schedule, now: DateTime<Tz>) -> DateTime<Tz> {
    let back =
        (7 + now.weekday().num_days_from_monday() - schedule.weekday.num_days_from_monday()) % 7;
    let date = now.date_naive() - Days::new(back.into());
    let slot = at(schedule, date);
    if slot <= now {
        slot
    } else {
        at(schedule, date - Days::new(7))
    }
}

/// The draw time on `date`; inside a daylight-saving gap, an instant an hour or so off.
fn at(schedule: &Schedule, date: NaiveDate) -> DateTime<Tz> {
    let local = date.and_time(schedule.time);
    let tz = schedule.timezone;
    tz.from_local_datetime(&local)
        .earliest()
        .unwrap_or_else(|| tz.from_utc_datetime(&local))
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{NaiveTime, Weekday};

    fn monday_ten() -> Schedule {
        Schedule {
            weekday: Weekday::Mon,
            time: NaiveTime::from_hms_opt(10, 0, 0).unwrap(),
            timezone: chrono_tz::Europe::Madrid,
        }
    }

    fn madrid(y: i32, m: u32, d: u32, h: u32, min: u32) -> DateTime<Tz> {
        chrono_tz::Europe::Madrid
            .with_ymd_and_hms(y, m, d, h, min, 0)
            .unwrap()
    }

    #[test]
    fn picks_the_latest_monday_ten_at_or_before_now() {
        let s = monday_ten();
        // Monday 2026-11-23
        assert_eq!(
            latest_slot(&s, madrid(2026, 11, 23, 10, 0)),
            madrid(2026, 11, 23, 10, 0)
        );
        assert_eq!(
            latest_slot(&s, madrid(2026, 11, 23, 9, 59)),
            madrid(2026, 11, 16, 10, 0)
        );
        assert_eq!(
            latest_slot(&s, madrid(2026, 11, 26, 18, 0)),
            madrid(2026, 11, 23, 10, 0)
        );
        assert_eq!(
            latest_slot(&s, madrid(2026, 11, 22, 23, 0)),
            madrid(2026, 11, 16, 10, 0)
        );
    }
}
