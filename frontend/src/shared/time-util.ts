export function getLocalTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

export function getDurationString(durationSeconds: number) {
  let hours = Math.floor(durationSeconds / 3600);
  let minutes = Math.floor((durationSeconds - hours * 3600) / 60);
  let seconds = Math.floor(durationSeconds - hours * 3600 - minutes * 60);

  return `${hours ? hours + "hr " : ""}${minutes ? minutes + "min " : ""}${seconds}s`;
}

export function getTimeText(date: Date): string {
  const now = new Date();
  const secondsAgo = getSecondsAgo(date, now);
  if (secondsAgo < 60) {
    return `${secondsAgo} seconds ago`;
  }
  const minutesAgo = getMinutesAgo(date, now);
  if (minutesAgo < 60) {
    return `${getMinutesAgo(date, now)} minutes ago`;
  }
  const hoursAgo = getHoursAgo(date, now);
  if (hoursAgo < 24) {
    return `${getHoursAgo(date, now)} hours ago`;
  }
  const daysAgo = getDaysAgo(date, now);
  if (daysAgo === 1) {
    return "Yesterday";
  }
  if (daysAgo < 7) {
    return `${daysAgo} days ago`;
  }
  const weeksAgo = getWeeksAgo(date, now);
  if (weeksAgo === 1) {
    return "Last week";
  }
  if (weeksAgo < 4) {
    return `${weeksAgo} weeks ago`;
  }
  const monthsAgo = getMonthsAgo(date, now);
  if (monthsAgo === 1) {
    return "Last month";
  }
  if (monthsAgo < 12) {
    return `${monthsAgo} months ago`;
  }
  const yearsAgo = getYearsAgo(date, now);
  if (yearsAgo === 1) {
    return "Last year";
  }
  return `${yearsAgo} years ago`;
}

export function getWeeksAgo(date, now) {
  const diffInTime = now.getTime() - date.getTime();
  return Math.floor(diffInTime / (1000 * 60 * 60 * 24 * 7));
}

export function getDaysAgo(date, now) {
  const diffInTime = now.getTime() - date.getTime();
  return Math.floor(diffInTime / (1000 * 60 * 60 * 24));
}

export function getMonthsAgo(date, now) {
  const diffInTime = now.getTime() - date.getTime();
  return Math.floor(diffInTime / (1000 * 60 * 60 * 24 * 30));
}

export function getYearsAgo(date, now) {
  const diffInTime = now.getTime() - date.getTime();
  return Math.floor(diffInTime / (1000 * 60 * 60 * 24 * 365));
}

export function getHoursAgo(date, now) {
  const diffInTime = now.getTime() - date.getTime();
  return Math.floor(diffInTime / (1000 * 60 * 60));
}

export function getMinutesAgo(date, now) {
  const diffInTime = now.getTime() - date.getTime();
  return Math.floor(diffInTime / (1000 * 60));
}

export function getSecondsAgo(date, now) {
  const diffInTime = now.getTime() - date.getTime();
  return Math.floor(diffInTime / 1000);
}
