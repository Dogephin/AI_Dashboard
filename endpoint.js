require('dotenv').config({ override: true });
const mysql = require('mysql2/promise');
const ZongJi = require('@powersync/mysql-zongji');

async function createPools() {
    // Source DB (Watches This)
    const sourcePool = await mysql.createPool({
        host: process.env.SOURCE_DB_HOST,
        port: process.env.SOURCE_DB_PORT,
        user: process.env.SOURCE_DB_USER,
        password: process.env.SOURCE_DB_PASSWORD,
        database: process.env.DB_WATCH_DATABASE
    });

    // Cloud target DB (Receives Live Changes)
    const targetPool = await mysql.createPool({
        host: process.env.DB_HOST,
        port: process.env.DB_PORT,
        user: process.env.DB_USER,
        password: process.env.DB_PASSWORD,
        database: process.env.DB_DATABASE
    });

    console.log(`Connected to SOURCE DB: ${process.env.DB_WATCH_DATABASE}`);
    console.log(`Connected to TARGET DB: ${process.env.DB_DATABASE}`);
    return { sourcePool, targetPool };
}

async function getPrimaryKeys(pool, schema, table) {
    const [rows] = await pool.query(
        `SHOW KEYS FROM \`${schema}\`.\`${table}\` WHERE Key_name = 'PRIMARY'`
    );
    return rows.map(r => r.Column_name);
}

async function startListener() {
    const { sourcePool, targetPool } = await createPools();
    const primaryKeyCache = {};
    const tableMap = {};

    // Source DB (Watches This)
    const zongji = new ZongJi({
        host: process.env.SOURCE_DB_HOST,
        port: process.env.SOURCE_DB_PORT,
        user: process.env.SOURCE_DB_USER,
        password: process.env.SOURCE_DB_PASSWORD,
    });

    zongji.on('binlog', async (event) => {
        console.log(`Event: ${event.getEventName()} | TableID: ${event.tableId}`);

        if (event.getEventName() === 'tablemap') {
            tableMap[event.tableId] = {
                tableName: event.tableName,
                schemaName: event.schemaName
            };
            console.log(`TableMap updated:`, tableMap[event.tableId]);
        }

        if (
            event.getEventName() === 'writerows' ||
            event.getEventName() === 'updaterows' ||
            event.getEventName() === 'deleterows'
        ) {
            const mapping = tableMap[event.tableId];
            if (!mapping) {
                console.warn(`⚠ No table mapping found for tableId ${event.tableId}`);
                return;
            }
            if (mapping.schemaName !== process.env.DB_WATCH_DATABASE) {
                console.log(`Skipping event from db ${mapping.schemaName}`);
                return;
            }

            console.log(`Change detected in ${mapping.schemaName}.${mapping.tableName}`);
            console.dir(event.rows, { depth: null });

            // Get primary keys from cache or DB
            if (!primaryKeyCache[mapping.tableName]) {
                primaryKeyCache[mapping.tableName] = await getPrimaryKeys(
                    sourcePool,
                    mapping.schemaName,
                    mapping.tableName
                );
                console.log(`Primary key(s) for ${mapping.tableName}:`, primaryKeyCache[mapping.tableName]);
            }
            const pkCols = primaryKeyCache[mapping.tableName];

            try {
                if (event.getEventName() === 'writerows') {
                    for (const row of event.rows) {
                        const cols = Object.keys(row);
                        const placeholders = cols.map(() => '?').join(',');
                        const sql = `INSERT INTO \`${mapping.tableName}\` (${cols.map(c => `\`${c}\``).join(',')})
                                        VALUES (${placeholders})
                                        ON DUPLICATE KEY UPDATE ${cols.map(c => `\`${c}\`=VALUES(\`${c}\`)`).join(',')}`;
                        await targetPool.query(sql, Object.values(row));
                        console.log(`INSERT replicated to ${mapping.tableName} in ${process.env.DB_DATABASE}`);
                    }
                }

                if (event.getEventName() === 'updaterows') {
                    for (const { before, after } of event.rows) {
                        const setCols = Object.keys(after).map(c => `\`${c}\`=?`).join(',');
                        const whereClause = pkCols.map(pk => `\`${pk}\`=?`).join(' AND ');
                        const sql = `UPDATE \`${mapping.tableName}\` SET ${setCols} WHERE ${whereClause}`;
                        await targetPool.query(sql, [...Object.values(after), ...pkCols.map(pk => before[pk])]);
                        console.log(`UPDATE replicated to ${mapping.tableName} in ${process.env.DB_DATABASE}`);
                    }
                }

                if (event.getEventName() === 'deleterows') {
                    for (const row of event.rows) {
                        const whereClause = pkCols.map(pk => `\`${pk}\`=?`).join(' AND ');
                        const sql = `DELETE FROM \`${mapping.tableName}\` WHERE ${whereClause}`;
                        await targetPool.query(sql, pkCols.map(pk => row[pk]));
                        console.log(`DELETE replicated to ${mapping.tableName} in ${process.env.DB_DATABASE}`);
                    }
                }
            } catch (err) {
                console.error(`Error replicating change:`, err);
            }
        }
    });

    zongji.on('error', (err) => {
        console.error(`ZongJi error:`, err);
    });

    zongji.start({
        startAtEnd: true,
        includeEvents: ['tablemap', 'writerows', 'updaterows', 'deleterows'],
        includeSchema: {
            [process.env.DB_WATCH_DATABASE]: true
        },
    });

    console.log(`ZongJi started, waiting for events from DB: ${process.env.DB_WATCH_DATABASE}`);
}

startListener().catch(err => {
    console.error(`Failed to start listener:`, err);
});
