export function groupLineupsByLandingPoint(points, lineups) {
  const pointById = new Map(points.map((point) => [point.id, point]));
  const byPoint = new Map();

  for (const lineup of lineups) {
    const group = byPoint.get(lineup.land_point_id) || [];
    group.push(lineup);
    byPoint.set(lineup.land_point_id, group);
  }

  return Array.from(byPoint.entries())
    .map(([pointId, group]) => {
      const point = pointById.get(pointId);
      return point ? { point, lineups: group } : null;
    })
    .filter(Boolean)
    .sort((a, b) => a.point.name.localeCompare(b.point.name));
}

export function buildLineupMediaCards(lineup) {
  if (!lineup) return [];
  const cards = [];

  if (lineup.start_point?.aim_image_url) {
    cards.push({
      title: '站位瞄点',
      description:
        lineup.start_point.aim_image_description
        || lineup.start_point.description
        || '站到这里后，再对准道具瞄点。',
      url: lineup.start_point.aim_image_url,
    });
  }

  if (lineup.aim_point?.aim_image_url && lineup.aim_point?.id !== lineup.start_point?.id) {
    cards.push({
      title: '道具瞄点',
      description:
        lineup.aim_point.aim_image_description
        || lineup.aim_point.description
        || '准星对准该位置后按步骤投掷。',
      url: lineup.aim_point.aim_image_url,
    });
  }

  if (lineup.land_point?.effect_image_url) {
    cards.push({
      title: '落点效果图',
      description:
        lineup.land_point.effect_image_description
        || lineup.land_point.description
        || '道具落点和实际遮挡效果。',
      url: lineup.land_point.effect_image_url,
    });
  }

  for (const [index, url] of (lineup.media || []).entries()) {
    cards.push({
      title: `补充截图 ${index + 1}`,
      description: '',
      url,
    });
  }

  return cards;
}
