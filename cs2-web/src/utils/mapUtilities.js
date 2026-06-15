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

export function buildLineupMediaCards(lineup, language = 'zh') {
  if (!lineup) return [];
  const cards = [];
  const copy = language === 'en'
    ? {
        standAimPoint: 'Position',
        standDescription: 'Stand here, then align to the crosshair aim point.',
        utilityAimPoint: 'Crosshair Aim',
        utilityDescription: 'Align your crosshair to this position, then throw by the steps.',
        effectImage: 'Landing effect',
        effectDescription: 'Utility landing point and real blocking effect.',
        extraImage: 'Extra image',
      }
    : {
        standAimPoint: '站位瞄点',
        standDescription: '站到这里后，再对准道具瞄点。',
        utilityAimPoint: '道具瞄点',
        utilityDescription: '准星对准该位置后按步骤投掷。',
        effectImage: '落点效果图',
        effectDescription: '道具落点和实际遮挡效果。',
        extraImage: '补充截图',
      };

  if (lineup.start_point?.aim_image_url) {
    cards.push({
      title: copy.standAimPoint,
      description:
        lineup.start_point.aim_image_description
        || lineup.start_point.description
        || copy.standDescription,
      url: lineup.start_point.aim_image_url,
    });
  }

  if (lineup.aim_point?.aim_image_url && lineup.aim_point?.id !== lineup.start_point?.id) {
    cards.push({
      title: copy.utilityAimPoint,
      description:
        lineup.aim_point.aim_image_description
        || lineup.aim_point.description
        || copy.utilityDescription,
      url: lineup.aim_point.aim_image_url,
    });
  }

  if (lineup.land_point?.effect_image_url) {
    cards.push({
      title: copy.effectImage,
      description:
        lineup.land_point.effect_image_description
        || lineup.land_point.description
        || copy.effectDescription,
      url: lineup.land_point.effect_image_url,
    });
  }

  for (const [index, url] of (lineup.media || []).entries()) {
    cards.push({
      title: `${copy.extraImage} ${index + 1}`,
      description: '',
      url,
    });
  }

  return cards;
}
