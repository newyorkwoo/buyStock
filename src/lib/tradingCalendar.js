/**
 * US Trading Calendar — detect whether today is a market trading day.
 */

/**
 * Fixed-date US market holidays (month is 0-indexed).
 * Holidays that fall on weekends are observed on Mon/Fri.
 */
function getFixedHolidays(year) {
  const holidays = [
    new Date(year, 0, 1),   // New Year's Day
    new Date(year, 6, 4),   // Independence Day
    new Date(year, 11, 25)  // Christmas
  ]

  // Juneteenth (since 2021)
  if (year >= 2021) holidays.push(new Date(year, 5, 19))

  return holidays
}

/** Get the nth weekday of a month (0=Sun..6=Sat). n=1 is the first. */
function nthWeekday(year, month, dayOfWeek, n) {
  const d = new Date(year, month, 1)
  while (d.getDay() !== dayOfWeek) d.setDate(d.getDate() + 1)
  d.setDate(d.getDate() + (n - 1) * 7)
  return d
}

/** Last Monday of a month. */
function lastMonday(year, month) {
  const d = new Date(year, month + 1, 0) // last day of month
  while (d.getDay() !== 1) d.setDate(d.getDate() - 1)
  return d
}

function getFloatingHolidays(year) {
  return [
    nthWeekday(year, 0, 1, 3),  // MLK Day — 3rd Mon Jan
    nthWeekday(year, 1, 1, 3),  // Presidents' Day — 3rd Mon Feb
    lastMonday(year, 4),         // Memorial Day — last Mon May
    nthWeekday(year, 8, 1, 1),  // Labor Day — 1st Mon Sep
    nthWeekday(year, 10, 3, 4), // Thanksgiving — 4th Thu Nov
  ]
}

/**
 * Adjust fixed holiday to observed date:
 * if Saturday → Friday; if Sunday → Monday.
 */
function observedDate(d) {
  const day = d.getDay()
  if (day === 6) return new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1)
  if (day === 0) return new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1)
  return d
}

function toKey(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/**
 * Check if a given date is a US stock market trading day.
 * @param {Date} [date] defaults to today
 * @returns {boolean}
 */
export function isTradingDay(date = new Date()) {
  const dow = date.getDay()
  if (dow === 0 || dow === 6) return false // weekend

  const year = date.getFullYear()
  const key = toKey(date)

  const allHolidays = [
    ...getFixedHolidays(year).map(observedDate),
    ...getFloatingHolidays(year)
  ]

  return !allHolidays.some((h) => toKey(h) === key)
}

/**
 * Check if a given date is a US market trading day,
 * or if market closed recently (within last 2 calendar days)
 * so we still want to update on non-trading days after a gap.
 * @param {Date} [date]
 * @returns {boolean}
 */
export function shouldAutoUpdate(date = new Date()) {
  // Always auto-update — user wants latest data whenever they open the app
  // on a trading day
  return isTradingDay(date)
}
