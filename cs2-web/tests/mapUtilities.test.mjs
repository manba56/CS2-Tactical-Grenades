import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildLineupMediaCards,
  groupLineupsByLandingPoint,
} from '../src/utils/mapUtilities.js';

test('groups multiple utility lineups by landing point', () => {
  const points = [
    { id: 1, name: 'A Site' },
    { id: 2, name: 'B Site' },
  ];
  const lineups = [
    { id: 10, land_point_id: 1, utility_type: 'smoke' },
    { id: 11, land_point_id: 1, utility_type: 'flash' },
    { id: 12, land_point_id: 999, utility_type: 'he' },
  ];

  const groups = groupLineupsByLandingPoint(points, lineups);

  assert.equal(groups.length, 1);
  assert.equal(groups[0].point.id, 1);
  assert.deepEqual(groups[0].lineups.map((lineup) => lineup.id), [10, 11]);
});

test('builds utility media cards from point and lineup media', () => {
  const cards = buildLineupMediaCards({
    start_point: {
      id: 1,
      aim_image_url: '/stand.png',
      aim_image_description: 'stand description',
    },
    aim_point: {
      id: 2,
      aim_image_url: '/aim.png',
      aim_image_description: 'aim description',
    },
    land_point: {
      id: 3,
      effect_image_url: '/land.png',
      effect_image_description: 'land description',
    },
    media: ['/extra.png'],
  });

  assert.deepEqual(cards.map((card) => card.title), [
    '站位瞄点',
    '道具瞄点',
    '落点效果图',
    '补充截图 1',
  ]);
  assert.deepEqual(cards.map((card) => card.url), [
    '/stand.png',
    '/aim.png',
    '/land.png',
    '/extra.png',
  ]);
});

test('does not duplicate aim media when start and aim point are the same point', () => {
  const cards = buildLineupMediaCards({
    start_point: {
      id: 1,
      aim_image_url: '/same.png',
    },
    aim_point: {
      id: 1,
      aim_image_url: '/same.png',
    },
    land_point: null,
    media: [],
  });

  assert.deepEqual(cards.map((card) => card.title), ['站位瞄点']);
});
