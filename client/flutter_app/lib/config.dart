// Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
// Copyright (C) 2025-2026  Davide Quirillo
// Licensed under the GNU GPL v3 or later. See LICENSE for details.
//
// Additional permission under GNU GPL version 3 section 7:
// This program may be linked with the "flutter_background_geolocation"
// plugin by Transistor Software. See the LICENSE file for full details.

const appName = 'Quidalert';
const apiBaseUrl = 'http://10.0.2.2:8000/api';

// The competence territory, examples:
// "Rome", "Milan", "Milan City and near", "California", "New York", etc. etc.
// It's simply an information for the users.
const competenceTerritory = 'Italy';
