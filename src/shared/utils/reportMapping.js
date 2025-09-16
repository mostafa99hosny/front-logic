//map frontend report

function mapFrontendToDB(frontendData) {
  return {
    report_title: frontendData.report_title,
    valuation_purpose: frontendData.purpose_of_assessment,
    value_premise: frontendData.value_hypothesis,
    report_type: frontendData.report_type,
    valuation_date: frontendData.evaluation_date,
    report_issuing_date: frontendData.report_release_date,
    assumptions: frontendData.assumptions,
    special_assumptions: frontendData.special_assumptions,
    final_value: frontendData.final_opinion_on_value,
    valuation_currency: frontendData.evaluation_currency,

    // Files
    report_asset_file: frontendData.uploaded_pdf_filename || "",

    // Clients
    clients: (frontendData.clients || []).map(c => ({
      client_name: c.client_name,
      telephone_number: c.telephone_number,
      email_address: c.email_address,
    })),

    // Other users
    has_other_users: frontendData.has_other_users_report,
    report_users: (frontendData.report_users || []).map(u => u.username),

    // Valuers (residents)
    valuers: (frontendData.residents || []).map(r => ({
      valuer_name: r.valuer_name,
      contribution_percentage: parseInt(
        String(r.contribution_percentage).replace('%', '')
      ),
    })),

    // Asset data
    asset_data: (frontendData.asset_data || []).map(a => ({
      id: a.asset_id,
      serial_no: a.serial_no,
      asset_type: a.asset_type,
      asset_name: a.asset_name,
      model: a.model,
      year_made: a.year_made,
      final_value: a.final_value,
      asset_usage_id: a.asset_usage_id,
      value_base: a.value_base,
      inspection_date: a.inspection_date,
      production_capacity: a.production_capacity,
      production_capacity_measuring_unit: a.production_capacity_measuring_unit,
      owner_name: a.owner_name,
      product_type: a.product_type,
      market_approach: a.market_approach,
      market_approach_value: a.market_approach_value,
      cost_approach: a.cost_approach,
      cost_approach_value: a.cost_approach_value,
      country: a.country,
      region: a.region,
      city: a.city,
    })),
  };
}



export default {
  mapFrontendToDB,
};
