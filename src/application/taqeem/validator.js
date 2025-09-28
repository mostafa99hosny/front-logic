const EXPECTED_COLUMNS = [
  "asset_type", "asset_name", "final_value", "asset_usage_id", "value_base", "inspection_date", "production_capacity", "production_capacity_measuring_unit", "owner_name", "product_type", "market_approach", "market_approach_value", "cost_approach", "cost_approach_value", "country", "region", "city"
];

const MANDATORY_FIELDS = [
  "asset_type", "asset_name", "asset_usage_id", "value_base", "inspection_date", "final_value", "production_capacity", "production_capacity_measuring_unit", "owner_name", "product_type", "market_approach", "market_approach_value", "country", "region", "city"
];

const ASSET_USAGE_MIN = 38;
const ASSET_USAGE_MAX = 56;
const VALUE_BASE_MIN = 1;
const VALUE_BASE_MAX = 9;
const MARKET_APPROACH_ALLOWED = new Set([0, 1, 2]);

function normalizeHeader(header) {
  return header.map(h => (h === null || h === undefined) ? '' : String(h).trim().toLowerCase());
}

function isEmpty(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string' && value.trim() === '') return true;
  if (typeof value === 'string' && value.trim().toLowerCase() === 'n/a') return false;
  if (value === '0') return false;
  return false;
}

function toInt(value) {
  if (isEmpty(value)) return [false, null];
  let s = String(value).trim();
  if (s.toLowerCase().endsWith('.0')) s = s.slice(0, -2);
  if (s.includes('.')) return [false, null];
  const n = parseInt(s, 10);
  if (isNaN(n)) return [false, null];
  return [true, n];
}

function toFloat(value) {
  if (isEmpty(value)) return [false, null];
  const n = parseFloat(String(value).trim());
  if (isNaN(n)) return [false, null];
  return [true, n];
}

function appendMessage(existing, newMsg) {
  if (existing === null || existing === undefined) return newMsg;
  const s = String(existing).trim();
  if (!s || s.toLowerCase() === 'nan') return newMsg;
  return `${s} | ${newMsg}`;
}

function checkMissingColumns(header) {
  const h = normalizeHeader(header);
  return EXPECTED_COLUMNS.filter(c => !h.includes(c));
}

function validateMandatoryOnly(rows, header) {
  header = normalizeHeader(header);
  let missingCount = 0;
  const highlights = {};
  const summary = [];

  rows.forEach((row, idx) => {
    MANDATORY_FIELDS.forEach(col => {
      const colIdx = header.indexOf(col);
      if (colIdx === -1) return;
      let val = row[colIdx];
      if (isEmpty(val)) {
        if (col === 'market_approach') return;

        if (col === 'market_approach_value') {
          const approachIdx = header.indexOf('market_approach');
          let approachRaw = approachIdx !== -1 ? row[approachIdx] : '';
          let approach = 0;
          if (!isEmpty(approachRaw)) {
            try { approach = parseInt(parseFloat(String(approachRaw).trim())); } catch { approach = null; }
          }
          if (approach === 0 || approach === null) return;
        }

        missingCount++;
        highlights[`${idx},${col}`] = 'yellow';
        row[colIdx] = appendMessage(row[colIdx], 'This mandatory field is empty');
      }
    });
  });

  if (missingCount === 0) {
    summary.push('✅ جميع الحقول الإلزامية مكتملة وصحيحة.');
  } else {
    summary.push(`❌ عدد الحقول الإلزامية الفارغة: ${missingCount}`);
  }
  return { rows, highlights, summary };
}

function validateFinalValueOnly(rows, header) {
  header = normalizeHeader(header);
  let issues = 0;
  const highlights = {};
  const summary = [];
  const colIdx = header.indexOf('final_value');
  if (colIdx === -1) return { rows, highlights, summary: ['final_value not found'] };

  rows.forEach((row, idx) => {
    let val = row[colIdx];
    let message = null;
    if (isEmpty(val)) {
      message = 'final_value is mandatory and cannot be empty';
    } else {
      const [ok] = toInt(val);
      if (!ok) message = 'Final value must be a non-decimal integer';
    }
    if (message) {
      issues++;
      highlights[`${idx},final_value`] = 'yellow';
      row[colIdx] = appendMessage(row[colIdx], message);
    }
  });

  if (issues === 0) {
    summary.push('✅ final_value values valid.');
  } else {
    summary.push(`❌ final_value errors: ${issues}`);
  }
  return { rows, highlights, summary };
}

function validateDatesOnly(rows, header) {
  header = normalizeHeader(header);
  let invalidCount = 0, autoFixed = 0;
  const highlights = {};
  const colIdx = header.indexOf('inspection_date');
  const summary = [];
  if (colIdx === -1) return { rows, highlights, summary: ["❌ العمود inspection_date غير موجود في الملف."] };

  rows.forEach((row, idx) => {
    let val = row[colIdx];
    if (isEmpty(val)) {
      highlights[`${idx},inspection_date`] = 'yellow';
      row[colIdx] = appendMessage(row[colIdx], 'Date must be in dd-mm-YYYY format');
      invalidCount++;
      return;
    }
    let s = String(val).trim();
    let dt = false;
    let formatted = null;
    // dd-mm-yyyy
    if (/^\d{2}-\d{2}-\d{4}$/.test(s)) {
      formatted = s;
      dt = true;
    } else if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
      // convert yyyy-mm-dd -> dd-mm-yyyy
      formatted = `${s.slice(8,10)}-${s.slice(5,7)}-${s.slice(0,4)}`;
      dt = true;
    }

    if (dt && formatted) {
      row[colIdx] = formatted;
      autoFixed++;
    } else {
      highlights[`${idx},inspection_date`] = 'yellow';
      row[colIdx] = appendMessage(row[colIdx], 'Date must be in dd-mm-YYYY format');
      invalidCount++;
    }
  });

  if (invalidCount === 0) {
    summary.push('✅ جميع التواريخ في inspection_date مكتملة وصحيحة.');
  } else {
    summary.push(`❌ عدد التواريخ غير الصحيحة في inspection_date: ${invalidCount}`);
    summary.push('↳ يجب أن يكون تنسيق التاريخ dd-mm-YYYY.');
  }
  if (autoFixed) summary.push(`تم تصحيح تنسيق ${autoFixed} تاريخ تلقائيًا.`);
  return { rows, highlights, summary };
}

function validateAssetUsageIdOnly(rows, header) {
  header = normalizeHeader(header);
  let issues = 0;
  const highlights = {};
  const summary = [];
  const colIdx = header.indexOf('asset_usage_id');
  if (colIdx === -1) {
    summary.push("❌ العمود asset_usage_id غير موجود في الملف.");
    return { rows, highlights, summary };
  }

  rows.forEach((row, idx) => {
    let val = row[colIdx];
    if (isEmpty(val)) return;
    const [ok, intval] = toInt(val);
    if (!ok || intval === null || intval < ASSET_USAGE_MIN || intval > ASSET_USAGE_MAX) {
      highlights[`${idx},asset_usage_id`] = 'yellow';
      row[colIdx] = appendMessage(row[colIdx], `asset_usage_id يجب أن يكون بين ${ASSET_USAGE_MIN} و ${ASSET_USAGE_MAX}`);
      issues++;
    }
  });

  if (issues === 0) {
    summary.push('✅ جميع البيانات في حقل asset_usage_id مكتملة وصحيحة.');
  } else {
    summary.push(`❌ عدد القيم غير الصحيحة في asset_usage_id: ${issues}`);
    summary.push('↳ يجب أن تكون جميع القيم في هذا الحقل بين 38 و 56.');
  }
  return { rows, highlights, summary };
}

function validateValueBaseOnly(rows, header) {
  header = normalizeHeader(header);
  let issues = 0;
  const highlights = {};
  const summary = [];
  const colIdx = header.indexOf('value_base');
  if (colIdx === -1) {
    summary.push("❌ العمود value_base غير موجود في الملف.");
    return { rows, highlights, summary };
  }

  rows.forEach((row, idx) => {
    let val = row[colIdx];
    if (isEmpty(val)) return;
    const [ok, intval] = toInt(val);
    if (!ok || intval === null || intval < VALUE_BASE_MIN || intval > VALUE_BASE_MAX) {
      highlights[`${idx},value_base`] = 'yellow';
      row[colIdx] = appendMessage(row[colIdx], `value_base يجب أن يكون بين ${VALUE_BASE_MIN} و ${VALUE_BASE_MAX}`);
      issues++;
    }
  });

  if (issues === 0) {
    summary.push('✅ جميع البيانات في حقل value_base مكتملة وصحيحة.');
  } else {
    summary.push(`❌ عدد القيم غير الصحيحة في value_base: ${issues}`);
    summary.push('↳ يجب أن تكون جميع القيم في هذا الحقل بين 1 و 9.');
  }
  return { rows, highlights, summary };
}

function validateMarketApproachOnly(rows, header) {
  // header = normalizeHeader(header);
  // let issues = 0;
  // const highlights = {};
  // const idxMarketApproach = header.indexOf('market_approach');
  // const idxMarketApproachValue = header.indexOf('market_approach_value');
  // const idxFinalValue = header.indexOf('final_value');
  const summary = [];

  // if (idxMarketApproach === -1) {
  //   summary.push("❌ العمود market_approach غير موجود في الملف.");
  //   return { rows, highlights, summary };
  // }

  // rows.forEach((row, idx) => {
  //   ...
  // });

  // if (issues === 0) {
  //   summary.push('✅ جميع البيانات في حقل market_approach مكتملة وصحيحة.');
  // } else {
  //   summary.push(`❌ عدد القيم غير الصحيحة في market_approach: ${issues}`);
  //   summary.push('↳ يجب أن تكون القيم في هذا الحقل 0 أو 1 أو 2، وإذا كانت 1 أو 2 يجب أن يكون market_approach_value مساويًا لـ final_value.');
  // }

  return { rows, highlights: {}, summary };
}

function validateCostApproachOnly(rows, header) {
  // header = normalizeHeader(header);
  // let issues = 0;
  // const highlights = {};
  // const idxMarketApproach = header.indexOf('market_approach');
  // const idxCostApproach = header.indexOf('cost_approach');
  // const idxCostApproachValue = header.indexOf('cost_approach_value');
  // const idxFinalValue = header.indexOf('final_value');
  const summary = [];

  // if (idxMarketApproach === -1 || idxCostApproach === -1) {
  //   summary.push("❌ الأعمدة المطلوبة غير موجودة (market_approach أو cost_approach)");
  //   return { rows, highlights, summary };
  // }

  // rows.forEach((row, idx) => {
  //   ...
  // });

  // if (issues === 0) {
  //   summary.push('✅ جميع البيانات في حقل cost_approach مكتملة وصحيحة.');
  // } else {
  //   summary.push(`❌ عدد القيم غير الصحيحة في cost_approach: ${issues}`);
  //   summary.push('↳ إذا كان market_approach = 0 يجب أن يكون cost_approach = 1 أو 2، وإذا كان 1 أو 2 يجب أن يكون cost_approach_value مساويًا لـ final_value.');
  // }

  return { rows, highlights: {}, summary };
}

function validateAll(rows, header) {
  header = normalizeHeader(header);
  let highlights = {};
  let summary = [];

  const mand = validateMandatoryOnly(rows, header);
  Object.assign(highlights, mand.highlights);
  summary = summary.concat(mand.summary);

  const finalVal = validateFinalValueOnly(rows, header);
  Object.assign(highlights, finalVal.highlights);
  summary = summary.concat(finalVal.summary);

  const dates = validateDatesOnly(rows, header);
  Object.assign(highlights, dates.highlights);
  summary = summary.concat(dates.summary);

  const assetUsage = validateAssetUsageIdOnly(rows, header);
  Object.assign(highlights, assetUsage.highlights);
  summary = summary.concat(assetUsage.summary);

  const valueBase = validateValueBaseOnly(rows, header);
  Object.assign(highlights, valueBase.highlights);
  summary = summary.concat(valueBase.summary);

  const marketApproach = validateMarketApproachOnly(rows, header);
  Object.assign(highlights, marketApproach.highlights);
  summary = summary.concat(marketApproach.summary);

  const costApproach = validateCostApproachOnly(rows, header);
  Object.assign(highlights, costApproach.highlights);
  summary = summary.concat(costApproach.summary);

  let extraIssues = 0;
  const idxProdCap = header.indexOf('production_capacity');
  if (idxProdCap !== -1) {
    rows.forEach((row, idx) => {
      let val = row[idxProdCap];
      if (isEmpty(val)) return;
      const [ok, fval] = toFloat(val);
      if (!ok || fval === null || fval < 0) {
        highlights[`${idx},production_capacity`] = 'yellow';
        row[idxProdCap] = appendMessage(row[idxProdCap], 'Must be a non-negative number');
        extraIssues++;
      }
    });
  }

  summary.push(`Additional rule violations: ${extraIssues}`);
  if (summary.length === 0 || summary.every(s => /: 0$/.test(s))) {
    summary.push('✅ جميع البيانات في هذا الفحص صحيحة.');
  }

  return { rows, highlights, summary };
}

module.exports = {
  EXPECTED_COLUMNS,
  MANDATORY_FIELDS,
  ASSET_USAGE_MIN,
  ASSET_USAGE_MAX,
  VALUE_BASE_MIN,
  VALUE_BASE_MAX,
  MARKET_APPROACH_ALLOWED,
  normalizeHeader,
  isEmpty,
  toInt,
  toFloat,
  appendMessage,
  checkMissingColumns,
  validateMandatoryOnly,
  validateFinalValueOnly,
  validateDatesOnly,
  validateAssetUsageIdOnly,
  validateValueBaseOnly,
  validateMarketApproachOnly,
  validateCostApproachOnly,
  validateAll
};
